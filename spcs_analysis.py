# -*- coding: utf-8 -*-
"""
Created on Mon Apr 12 10:15:48 2021

@author: Victor
"""

import os
import pathlib
import asyncio

import numpy as np
import pandas as pd

from pyNastran.utils.nastran_utils import run_nastran
from pyNastran.bdf.cards.properties.shell import PCOMP

from nastran.aero.analysis.panel_flutter import PanelFlutterAnalysisModel
from nastran.aero.panels import SuperAeroPanel5
from nastran.aero.post import read_f06

#%% paths for input, output and the nastran exec
base_path = pathlib.Path().absolute()
nastran_exe = r'C:\Program Files\MSC.Software\NaPa_SE\2020\Nastran\bin\nast20200.exe'

#%% Calc Adimensional Dynamic Pressure


def sym_ply(theta, nplies): # theta, -theta, -theta, theta
    # assert nplies % 2 == 0
    thetas = []
    for i in range(int(nplies/2)):
        if i % 2 == 0:
            thetas.append(float(-theta))
        else:
            thetas.append(float(theta))
    return thetas[::-1] + thetas

def create_pcomp(analysis, theta, thick, nplies):
    mids = [analysis.model.materials[1].mid]*nplies
    thicknesses = [thick]*nplies
    thetas = sym_ply(theta, nplies)
    return PCOMP(1, mids, thicknesses, thetas)

def run_case(filename):
    rc = run_nastran(os.path.join(base_path,"analysis-bdf",filename), nastran_cmd=nastran_exe)
    print("{} {}".format(filename, rc[0]))
    return rc


from concurrent.futures import ThreadPoolExecutor
_executor = ThreadPoolExecutor(max_workers=4)

async def a_run_case(filename):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor,
                               lambda: run_nastran(
                                   os.path.join(base_path,"analysis-bdf",filename),
                                   nastran_cmd=nastran_exe))
    print("Runned {}".format(filename))

def read_results(analysis, theta_range, case_files_):
    df_results = []
    
    for i, fn in enumerate(case_files_.values()):
        print("Reading... {}".format(fn))
        df_data = read_f06(os.path.join(base_path,"analysis-bdf",fn.replace('bdf', 'f06').lower()), analysis.subcases[1])
        df_results.append(pd.concat({ theta_range[i]: df_data}, names=['THETA']))
        
    return pd.concat(df_results)



def calc_adm_dyn_pressure(vel, mach, D, analysis):
    vref = analysis.subcases[1].vref
    a = analysis.subcases[1].ref_chord
    rho = analysis.subcases[1].ref_rho
    return (rho * (vel * vref) ** 2) * (a ** 3) / (np.sqrt(mach ** 2 - 1) * D)

def plate_stiffs(df, D11s):
    thetas = df.index.get_level_values('THETA')
    return [D11s[theta] for theta in thetas]

def machs_df(df):
    return df.index.get_level_values('MACH NUMBER')

def preprocess_analysis(input_file, machs, n_vel, min_vel, max_vel, ab, nplies, thick, step):
    N = int(90/step)+1
    theta_range = np.linspace(0, 90, N)
    
    
    sub_data = {
        'type': 'PANELFLUTTER',
        'vref': 1000.,                      # used to calculate the non-dimensional dynamic pressure must be the same in control case (mm/s in the case)
        'ref_rho': 1.225e-12,               # air density reference (ton/mm^3 in the case)
        'ref_chord': 300.,                  # reference chord (mm in the case)
        'n_modes': 15,                      # number searched modes in modal analysis
        'frequency_limits': 
            [.0, 3000.],                    # the range of frequency (Hz) in modal analysis
        'method': 'PK',                     # the method for solving flutter (it will determine the next parameters
        'densities_ratio': [.5],            # rho/rho_ref -> 1/2 simulates the "one side flow" of the panel
        'machs': machs,# 4.5, 5.5, 6.5],    # Mach number
        'alphas': [.0]*len(machs),          # AoA (°) -> 0 is more conservative
        'reduced_frequencies': 
            [.001, .01, .1, .2, .4, .8],    # reduced frequencies (k)
        'velocities':                       # velocities (mm/s in the case)
            np.linspace(min_vel, max_vel, n_vel)*1000
        }
                
    analysis = PanelFlutterAnalysisModel()
        
    analysis.create_subcase_from_data(1, sub_data)
    analysis.import_from_bdf(input_file)
    
    edges_nodes_ids = edges_nodes_models[ab]
    corner_nodes = corner_models[ab]
    
    #
    spanel_p = SuperAeroPanel5(1)  # init panel
    xyz = [analysis.model.nodes[i].xyz for i in corner_nodes]
    spanel_p.set_panel_limits(*xyz)
    a = 20
    b_opt = {1: 20, 2: 10, 6: 6, 7: 20, 0.5: 40}
    spanel_p.set_mesh_size(b_opt[ab], a)
    spanel_p.init()
    
    analysis.add_superpanel(spanel_p)
    analysis.write_cards()  # write the panels on the pyNastran bdf interface
    
    del analysis.model.case_control_deck.subcases[1]

    for i, label in cases.items():
        analysis.model.case_control_deck.create_new_subcase(i)
        analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'LABEL = {}'.format(label))
        analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'METHOD = 1')
        analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'FMETHOD = 1')
        analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'ECHO=NONE')
        # analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'DISP=ALL')
        analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'SPC = {}'.format(i))
    
    # analysis.model.add_param('POST', [-1])
    analysis.model.add_param('VREF', [1000.0])
    analysis.model.add_param('COUPMASS', [1])
    analysis.model.add_param('LMODES', [20])
    
    for i, spcs in spc_cases.items():
        for comp, nds in zip(list(spcs), edges_nodes_ids.values()):
            if comp == '':
                continue
            analysis.model.add_spc1(i, comp, nds, comment=cases[i])

    prefix = "PFLUTTER-CFRP-AB-{}-NPLIES-{}-SYM".format(ab, nplies)
    
    case_files = dict()
    D11 = 0
    D11s = dict()
    
    for i, theta in enumerate(theta_range):
        filename = "{prefix}-THETA-{}.bdf".format(theta, prefix=prefix)
        pcomp = create_pcomp(analysis, theta, thick, nplies)
        analysis.model.properties[pcomp.pid] = pcomp
        analysis.model.properties[pcomp.pid].cross_reference(analysis.model)
        D = analysis.model.properties[pcomp.pid].get_individual_ABD_matrices()[2]
        
        if theta == 0:
            D11 = D[0][0]
        
        D11s[theta] = D[0][0]
            
        analysis.export_to_bdf("analysis-bdf/"+filename)  # exports to bdf file
        case_files[i+1] = filename
    
    data_rows_size = len(machs)*n_vel*len(cases)*len(theta_range)*15
    
    print(D11s)
    
    print("Expected data rows: {} rows.".format(data_rows_size))
    print("Expected data size: {} MB".format(data_rows_size*64*7/8e6))
    
    print("D11(theta=0) = {}".format(D11))    
    
    return analysis, theta_range, case_files, D11, prefix

def run_analysis(case_files):   
    
    for fn in case_files.values():
        run_case(fn)

async def a_run_analysis(case_files):
    tasks = []
    for fn in case_files.values():
        tasks.append(asyncio.create_task(a_run_case(fn)))
    
    await asyncio.gather(*tasks)

def postprocess_analysis(analysis, theta_range, case_files, D11):
    
    df = read_results(analysis, theta_range, case_files)
    
    print(df.info())
        
    df['LAMBDA'] = calc_adm_dyn_pressure(df.VELOCITY,
                                         machs_df(df),
                                         [D11]*len(df),
                                         analysis)

    return df

def get_critical_points(df_):
    epsilon = 0.001
    critic_idx = df_.loc[df_.DAMPING >= epsilon, 'VELOCITY'].groupby(
        ['THETA','SUBCASE', 'MACH NUMBER']).apply(
            lambda df: df.idxmin())
    
    critic_modes_idx = critic_idx.apply(lambda i: i[:-1])
    
    # critic = [df_.loc[idx] for idx in points.to_list()]    
    
    interp_data = []
    
    for idx in critic_modes_idx.to_list():
        
        df_s = df_.loc[idx]
        
        
        positive_damp_idx = df_s.DAMPING >= epsilon
        if not any(positive_damp_idx):
            continue
            
        # first row after flutter (damp >= 0)
        upper_row = df_s.loc[positive_damp_idx].iloc[0,:]
        
        # row before the flutter condition
        if upper_row.name > 0:
            lower_row = df_s.loc[upper_row.name-1,:] 
        else:
            lower_row = df_s.loc[upper_row.name,:] 
        
        # new row with damp = 0 to be interpolated
        new_row = pd.Series([None, None, None, .0, None, None, None, None],
                            index=upper_row.index, name=-1)
        
        # concat rows and interpolate values
        interp_df = pd.concat([lower_row, new_row, upper_row], axis=1).T.interpolate()
        
        # get interpolated row
        interp_row = interp_df.loc[-1]
        
        # create a new DataFrame
        multi_idx = pd.MultiIndex.from_tuples([idx], names=df_.index.names[:-1])
        refact_df = pd.DataFrame([interp_row.to_numpy()],
                                 index=multi_idx,
                                 columns=df_.columns)
        interp_data.append(refact_df)
        
    return pd.concat(interp_data)


def print_max_min(df):
    print("Max:")
    print(df[['VELOCITY', 'LAMBDA']].max())
    print("\n")
    print("Min:")
    print(df[['VELOCITY', 'LAMBDA']].min())


#%%

cases = {1: "Loaded edges SS & unloaded edges SS",
         2: "Loaded edges SS & unloaded edges CP",
         3: "Loaded edges SS & unloaded edges SS/CP",
         4: "Loaded edges SS & unloaded edges SS/FF",
         5: "Loaded edges SS & unloaded edges CP/FF",
         6: "Loaded edges SS & unloaded edges FF",
         7: "Loaded edges CP & unloaded edges SS",
         8: "Loaded edges CP & unloaded edges CP",
         9: "Loaded edges CP & unloaded edges SS/CP",
         10: "Loaded edges CP & unloaded edges SS/FF",
         11: "Loaded edges CP & unloaded edges CP/FF",
         12: "Loaded edges CP & unloaded edges FF",
         }

spc_cases = {
        1: ('123', '123', '123', '123'),       # loaded edges SS, unloaded edges SS
        2: ('123', '123', '123456', '123456'), # loaded edges SS, unloaded edges CP
        3: ('123', '123', '123', '123456'),    # loaded edges SS, unloaded edges SS/CP
        4: ('123', '123', '123', ''),          # loaded edges SS, unloaded edges SS/FF
        5: ('123', '123', '123456', ''),       # loaded edges SS, unloaded edges CP/FF
        6: ('123', '123', '', ''),             # loaded edges SS, unloaded edges FF
        7: ('123456', '123456', '123', '123'),       # loaded edges CP, unloaded edges SS
        8: ('123456', '123456', '123456', '123456'), # loaded edges CP, unloaded edges CP
        9: ('123456', '123456', '123', '123456'),    # loaded edges CP, unloaded edges SS & CP
        10:('123456', '123456', '123', ''),          # loaded edges CP, unloaded edges SS & FF
        11:('123456', '123456', '123456', ''),       # loaded edges CP, unloaded edges CP & FF
        12:('123456', '123456', '', ''),             # loaded edges CP, unloaded edges FF
        }

edges_nodes_models = {
                    1:
                    {  
                     'front': [1] + list(range(61, 80+1)),
                     'back': list(range(21, 41+1)),
                     'left': list(range(2, 20+1)),
                     'right': list(range(42, 60+1)),
                     },
                    2: {  
                     'front': [1] + list(range(51, 60+1)),
                     'back': list(range(21, 31+1)),
                     'left': list(range(2, 20+1)),
                     'right': list(range(32, 50+1)),
                     },
                    6: {  
                     'front': [1] + list(range(47, 52+1)),
                     'back': list(range(21, 27+1)),
                     'left': list(range(2, 20+1)),
                     'right': list(range(28, 46+1)),
                     },
                    7: {  
                     'front': [1] + list(range(221, 240+1)),
                     'back': list(range(101, 121+1)),
                     'left': list(range(2, 100+1)),
                     'right': list(range(122, 220+1)),
                     },
                    0.5: {  
                     'front': [1] + list(range(81, 120+1)),
                     'back': list(range(21, 61+1)),
                     'left': list(range(2, 20+1)),
                     'right': list(range(62, 80+1)),
                     },
                    }

corner_models = { 1: [1, 21, 41, 61],
                  2: [1, 21, 31, 51],
                  6: [1, 21, 27, 47],
                  7: [1, 101, 121, 221],
                  0.5: [1, 21, 61, 81]
                 }

model_files = {
        1: r'base_plate.dat',
        2: r'ab=2_model.dat',
        6: r'ab=6_model.dat',
        7: r'ab=6_ref_model.dat',
        0.5: r'ab=05_model.dat'
    }




machs = [6.]
n_vel = 300
min_vel = 900.
max_vel = 5000.
thick = 0.5
nplies = 4 # 2, 4, 6, 8
ab = 0.5
step = 30

#%% Preprocess
input_file = os.path.join(base_path, model_files[ab])
analysis, theta_range, case_files, D11, prefix = preprocess_analysis(
    input_file, machs, n_vel, min_vel, max_vel, ab, nplies, thick, step=step) 

#%% Run Async

task = asyncio.create_task(a_run_analysis(case_files))

#%% Post Process

df = postprocess_analysis(analysis, theta_range, case_files, D11)


#%% Process critical points

flutter_df = get_critical_points(df)
flutter_df.groupby(level='MACH NUMBER').apply(print_max_min)

#%% Plot each

thetas_list = 'flutter_df.index.get_level_values('THETA')'.unique().to_list()

for m in machs:
    plot_flutter(flutter_df, cases, m, thetas_list)
    
#%% Save to pickle

save = True
if save:
    df.to_pickle(prefix+'.pkl.zip')

#%% Load pickle

# df = pd.read_pickle(prefix+'.pkl.zip')
df = pd.read_pickle(prefix+'.pkl.zip')

#%% Plot

import matplotlib.pyplot as plt

from cycler import cycler

monochrome = (cycler('color', ['k']) * cycler('marker', ['', '.']) *
              cycler('linestyle', ['solid', 'dashed', 'dashdot']))

# import matplotlib
# matplotlib.use("pgf")
# matplotlib.rcParams.update({
#     "pgf.texsystem": "pdflatex",
#     'font.family': 'serif',
#     'text.usetex': True,
#     'pgf.rcfonts': False,
# })

plt.style.use('grayscale')  
# plt.rc('font', family='serif')
# plt.rc('xtick', labelsize='x-small')
# plt.rc('ytick', labelsize='x-small')
plt.rc('text', usetex=False)
plt.rc('axes', prop_cycle=monochrome)

labels = [
         "SS",
         "CP",
         "SS/CP",
         "SS/FF",
         "CP/FF",
         "FF",
         ]


def plot_single(df_, cases, labels, title, mach, theta_range):
    fig = plt.figure()
    ax = fig.gca()
    
    df_ = df_.xs(mach, level='MACH NUMBER')
    
    for k, label in zip(cases, labels):
        adm_dyn_press = df_.xs(k, level='SUBCASE').LAMBDA
        theta = np.array(adm_dyn_press.index.get_level_values('THETA'))
        if len(adm_dyn_press) < len(theta_range):
            print("Warning on subcase {}".format(k))
            print("len(adm_dyn_press) = {}".format(len(adm_dyn_press)))
            print("len(theta) = {}".format(len(theta_range)))
        ax.plot(theta, adm_dyn_press, label=label, markevery=5)
            
    
    ax.set_xlabel(r'$\theta$ [°]')
    ax.set_ylabel(r'$\lambda$*')
    ax.set_title(title, fontsize=16)
    ax.grid()
    ax.legend()
    
    savef = False
    if savef:
        plt.savefig('figures/{}.png'.format(title.replace(r'/', '_')), dpi=800)
    
    return fig

def plot_flutter(df_, cases, mach, thetas):

    cases_SS = list(cases.keys())[:6]
    title_SS = r'CFRP; a/b={}; N={}; Perpendicular edges SS'.format(ab, nplies)
    f1 = plot_single(df_, cases_SS, labels, title_SS, mach, thetas)
    
    cases_CP = list(cases.keys())[6:]
    title_CP = r'CFRP; a/b={}; N={}; Perpendicular edges CP'.format(ab, nplies)
    f2 = plot_single(df_, cases_CP, labels, title_CP, mach, thetas)
    
    return (f1, f2)

def plot_double(df_, cases, thetas):
    fig, axs = plt.subplots(2, sharex=True, sharey=True)

    title = r'CFRP; a/b={}; N={}'.format(ab, nplies)
    fig.suptitle(title)

    for k, label in zip(list(cases.keys())[:6], labels):
        adm_dyn_press = df_.xs(k, level='SUBCASE').LAMBDA
        theta = adm_dyn_press.index.get_level_values('THETA')
        if len(adm_dyn_press) < len(thetas):
            print("Warning on subcase {}".format(k))
            print("len(adm_dyn_press) = {}".format(len(adm_dyn_press)))
            print("len(theta) = {}".format(len(thetas)))
        axs[0].plot(theta, adm_dyn_press, label=label, markevery=4)
        
    axs[0].set_title('Perpendicular edges SS', fontsize=10)
    axs[0].set_ylabel(r'$\lambda$*')
    axs[0].label_outer()
    axs[0].grid()
    axs[0].legend(bbox_to_anchor=(0.77,0.31))
    
    for k, label in zip(list(cases.keys())[6:], labels):
        adm_dyn_press = df_.xs(k, level='SUBCASE').LAMBDA
        theta = adm_dyn_press.index.get_level_values('THETA')
        if len(adm_dyn_press) < len(thetas):
            print("Warning on subcase {}".format(k))
            print("len(adm_dyn_press) = {}".format(len(adm_dyn_press)))
            print("len(theta) = {}".format(len(thetas)))
        axs[1].plot(theta, adm_dyn_press, label=label, markevery=4)
    
    axs[1].set_title('Perpendicular edges CP', fontsize=10)        
    axs[1].set_ylabel(r'$\lambda$*')
    axs[1].set_xlabel(r'$\theta$ [°]')
    axs[1].grid()
    
    save = True
    if save:
        plt.savefig('figures/{}.png'.format(title.replace(r'/', '_')), dpi=800)



#%%
plot_double(flutter_df, cases, thetas_list)

#%%
def plot_f_g(df, theta, subcase, only_critic=True):
    df_list = list(df.xs((theta,subcase) , level=['THETA', 'SUBCASE']).groupby(level=['POINT']))
    fig, axs = plt.subplots(2)
    
    for point, df in df_list:
        lamb = df.LAMBDA
        freq = df.FREQUENCY
        damp = df.DAMPING
        if only_critic and not any(damp > .001):
            continue
        axs[0].plot(lamb, freq, label="Mode {}".format(int(point)), markevery=4)
        axs[1].plot(lamb, damp, markevery=4)
    
    axs[0].grid()
    axs[1].grid()
    fig.legend()
    return fig

plot_f_g(df, 90, 1, only_critic=True)

#%%

fig = plt.figure()
ax = fig.gca()

m = ['^', 'o', 'd', 'x', '>', '<']
idx = 0
for i, p_df in list(flutter_df.groupby(level='POINT')):
    print(i)
    ax.scatter(p_df.index.get_level_values('THETA').to_numpy(),
               p_df.index.get_level_values('SUBCASE').to_numpy(),
               label="Mode {}".format(int(i)),
               marker=m[idx])
    idx += 1

ax.legend()    

#%%

c_labels = {1: "SS",
         2: "Loaded edges SS & unloaded edges CP",
         3: "Loaded edges SS & unloaded edges SS/CP",
         4: "SS/FF",
         5: "Loaded edges SS & unloaded edges CP/FF",
         6: "FF",
         7: "SS",
         8: "Loaded edges CP & unloaded edges CP",
         9: "Loaded edges CP & unloaded edges SS/CP",
         10: "SS/FF",
         11: "Loaded edges CP & unloaded edges CP/FF",
         12: "FF",
         }

fig, axs = plt.subplots(2, sharex=True)
# fig.suptitle(r'Mach Number vs. critical $\lambda$; $\theta$ = 0')

for sub_k in [1, 4, 6]:
    df_ = flutter_df.xs(sub_k, level='SUBCASE').xs(0., level='THETA')
    label = c_labels[sub_k]
    axs[0].plot(df_.index.get_level_values('MACH NUMBER'), df_.LAMBDA, label=label)
        
axs[0].set_title('Perpendicular edges SS', fontsize=10)
# set_xlabel(r'$M$')
axs[0].set_ylabel(r'$\lambda$')
axs[0].label_outer()
axs[0].grid()
axs[0].legend()
# axs[0].legend(bbox_to_anchor=(1, 1.05))

# fig = plt.figure()
# ax = fig.gca()
for sub_k in [7, 10, 12]:
    df_ = flutter_df.xs(sub_k, level='SUBCASE').xs(0., level='THETA')
    label = c_labels[sub_k]
    axs[1].plot(df_.index.get_level_values('MACH NUMBER'), df_.LAMBDA, label=label)

axs[1].set_title('Perpendicular edges CP', fontsize=10)        
axs[1].set_ylabel(r'$\lambda$')
axs[1].set_xlabel(r'$M$')
# ax.set_xlabel(r'$M$')
# ax.set_ylabel(r'$\lambda$')
# ax.set_title(r'Mach Number vs. critical $\lambda$; Perpendicular edges CP; $\theta$ = 0', fontsize=16)
axs[1].grid()
# axs[1].legend()

fig.savefig('mach vs lambda.png', dpi=800)