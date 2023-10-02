# MCGG : Symbolic Model Checker for Graph Games

MCGG is a python based tool that can be used for checking properties on graph games using symbolic model checking techniques. The package requires [Python](https://www.python.org/downloads/release/python-3818/). And the packages mentioned in `requirements.txt` which can be installed by running the following command.

```shell
pip install requirements.txt
```

To use the tool, run the following command,
```shell
python model_checker.py <model_file> <formula_file>
```

To draw the figure which model checking run the following command,
```shell
python model_checker.py <model_file> <formula_file> -draw
```

The folders `Models` and `Formulas` contain example models and formulas.
