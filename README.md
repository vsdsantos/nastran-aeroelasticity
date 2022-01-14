[![DeepSource](https://static.deepsource.io/deepsource-badge-light-mini.svg)](https://deepsource.io/gh/zuckberj/nastran-aero-flutter/?ref=repository-badge)

# nastran-aeroelasticity

This project is intended to analyze the Supersonic Panel Flutter using the NASTRAN routines.
It has pre and post processing routines to generate the NASTRAN models and parse the results.

The project uses the pyNastran and the python scientific packages (i.e., scipy, numpy, matplotlib).

Currently, the focus is to use the aerodynamic Piston Theory, available on NASTRAN with the CAERO5 element.
But it can be extended to use with any aerodynamic element.

This software is result of a research project of the Department of Mechanical Engineering
at the Federal University of Minas Gerais (UFMG).

Please, [cite us](./docs/cite-us.md) if you use this project.

## What is Panel Flutter?

Panel Flutter is a specific aeroelastic phenomena studied in the aerospace engineering field. It is a dynamic instability resulted from the interaction of aerodynamic, elastic and inertial forces (and thermal stresses). It usually can happen at supersonic speeds (M > 1.2) mostly because the needed energy to provide instability in such structure (a panel) is high. When we say "dynamic instability", this means that response (or amplitude) in displacement of the given panel will grow exponentially. In fact, the growth is limited by the non-linear effects (normally structural), but induces very high cyclic stresses in the structure, and in consequence reduces its fatigue life.

## What is NASTRAN?

NASTRAN (acronym for NAsa STRuctural ANalysis) is a software originally made by NASA in FORTRAN for structural analysis. It has become public domain since (??), and after that CAE companies had developed the code further, but closely.
Today -- actually since the 70's -- it have many capabilities, including aeroelastic analysis.

Some efforts in the FOSS version of Nastran are placed in the [MYSTRAN](https://www.mystran.com/).

## Use

Some examples of utilization are placed on the [notebooks](./notebooks) directory. Please refer to them. Some documentation shall be made soon.

Here are some resulting plots made with the package.

![V-f](https://i.imgur.com/4yHdjqo.png)

![V-g](https://i.imgur.com/fnTF7IR.png)

## Contributing

Please, make a fork of the project, a PR and be clear in the intends and modifications made.
Thank you for the interest!
