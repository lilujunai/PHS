# phs ParallelHyperparameterSearch

phs is an ergonomic tool for performing hyperparameter searches on numerous cumpute instances of any arbitrary python function. This is achieved with minimal modifications inside your custom function. Possible applications appear in numerical computations which strongly depend on hyperparameters such as machine learning.

## Functionality
+ capable of all kinds of parameter types such as continuous or discrete numerical values, categorical values and even arbitrary python statements
+ no binding to a particular python framework like TensorFlow or PyTorch
+ possible search strategies are explicit specification, random search and Bayesian optimization
+ no limitation to the number of hyperparameter
+ parameter types and search strategies can be mixed for each parameter set as you like
+ handy monitor and visualization functions for supervising the the progress are already built-in
+ (fault tolerance)

## Installation
In order to use the full functionality of phs just clone this git repository to a local folder. Since phs itself is based on the package called phs you have to simply import it in your script.

## Quick Start
The easiest way to become familiar with the tool is to go through the following example of finding minima of the second order [Griewank function][2] which is a common test scenario for optimization algorithms. Code with respective output can be found in the examples folder.

+ Declare your phyton script as a function with a single argument named ```parameter```
+ Delete (or comment out) all hard coded parameter definitions you want to control with phs tool
+ add ```exec(parameter['hyperpar'],globals(),globals())```
+ return a meaningful parameter

**exemplary test function**

```python
import math as ma

def test_griewank(parameter):
    exec(parameter['hyperpar'],globals(),globals())
    z = (x*x+y*y)/4000 - ma.cos(x)*ma.cos(y/ma.sqrt(2)) + 1
    return z
```
+ create a new script to define a phs experiment (customize ```repository_root_dir```and the arguments ```working_dir, custom_module_root_dir, custom_module_name``` of the class instantiation):

**exemplary phs experiment**

```python
repository_root_dir = 'path/to/repository' #(example:'/home/NAME')

import sys
sys.path.append(repository_root_dir + '/parallel_hyperparameter_search/phs')

from phs import parallel_hyperparameter_search

hs = parallel_hyperparameter_search.ParallelHyperparameterSearch(experiment_name='experiment_griewank_1',
                                                                 working_dir='/absolute/path/to/a/folder/your/experiments/should/be/saved',
                                                                 repository_root_dir,
                                                                 custom_module_root_dir='/absolute/path/to/root/dir/in/which/your/test_function/resides',
                                                                 custom_module_name='file_name_with_test_function_definition_(without_extension)',
                                                                 custom_function_name='test_griewank',
                                                                 parallelization='processes',
                                                                 parameter_data_types={'x':float,'y':float})

for i in range(20):
    hs.add_random_numeric_parameter(parameter_name='x',bounds=[-5,5],distribution='uniform',round_digits=3)
    hs.add_random_numeric_parameter(parameter_name='y',bounds=[-5,5],distribution='uniform',round_digits=3)
    hs.register_parameter_set()

for i in range(10):
    hs.add_bayesian_parameter(parameter_name='x',bounds=[-5,5],round_digits=3)
    hs.add_bayesian_parameter(parameter_name='y',bounds=[-5,5],round_digits=3)
    hs.register_parameter_set(ignore_duplicates=False)

hs.show_parameter_set()

hs.start_execution()
```




## Parallelization Technique
At the moment two general types of parallelization are implemented, a third is under development. All of these share the same functionalities but differ in definition of workers and underlaying technology of task scheduling. On the software side there is one lightweight master. It runs the parameter setup, manages the task scheduling to the workers and gathers the results immediately as they are completed. Some monitoring and visualization possibilities are already build in. This way the user can observe and evaluate the progress. These functionalities can be customized, extended or performed only once after the last task.

Each function evaluation is done on a single worker. Even the Bayesian optimization for suggesting new parameter values is done on the workers themself. By this means the master is relieved and the prerequisites for a solid scaling behavior are ensured.

### DASK
[Dask][1] is a flexible library for parallel computing in Python. It provides dynamic task scheduling and 'Big Data' collections. Hereof futures are enough to schedule tasks to the workers. Dask is meant to be the parallelization backend for productive usage.

The definition and setup of one scheduler and multiple workers is done automatically in the background during the initialization routines of a multinode job on the Carme Cluster. Currently two workers are started on each node. Every worker sees one of the two GPUs of a node exclusively, while owning 4 CPU cores each. This static environment will be customizable to meet different use cases in the future.

### Processes
Beside Dask native processes of the Python build in concurrent.futures module is implemented as an alternative backend. It provides the same functionalities and user experience. Local processes serve as workers which means that the CPU cores of one node can be utilized exclusively but the GPU is always shared among the processes. In this case reserving a multinode job makes no sense. The intention of this kind of computing resources is less on the GPU heavy machine learning domain in terms of productive use but rather on testing and debugging especially when only one node is avaiable. But taking CPU only function evaluations into account the processes version can also be utilized in a meaningfull manner.


[1]: http://docs.dask.org/en/latest/index.html "DASK"
[2]: https://en.wikipedia.org/wiki/Griewank_function "Griewank"

## Author

Peter Michael Habelitz  
Fraunhofer-Institut für Techno- und Wirtschaftsmathematik ITWM  
Fraunhofer-Platz 1, 67663 Kaiserslautern, Germany  
Tel: +49 631 31600-4942, Fax: +49 631 31600-5942  
<peter.michael.habelitz@itwm.fraunhofer.de>