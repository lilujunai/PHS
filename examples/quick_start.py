import phs.parallel_hyperparameter_search  # standalone import
# Make sure that python can import 'phs'.
# One way is to run the 'install.sh' script provided within this project.

# import CarmeModules.HyperParameterSearch.phs.parallel_hyperparameter_search as phs  # import on Carme
import phs.parameter_definition  # standalone import

pardef = phs.parameter_definition.ParameterDefinition()

pardef.set_data_types_and_order([('x', float), ('y', float)])

pardef.add_individual_parameter_set(
    number_of_sets=20,
    set={'x': {'type': 'random', 'bounds': [-5, 5], 'distribution': 'uniform', 'round_digits': 3},
         'y': {'type': 'random_from_list', 'lst': [1.2, 3.4, 5.4, 6.3]}},
    prevent_duplicate=True)

pardef.add_individual_parameter_set(
    number_of_sets=10,
    set={'x': {'type': 'bayesian', 'bounds': [-5, 5], 'round_digits': 3},
         'y': {'type': 'bayesian', 'bounds': [-5, 5], 'round_digits': 3}})

pardef.export_parameter_definitions(export_path='absolute/path/to/parent/folder/for/export')

hs = phs.parallel_hyperparameter_search.ParallelHyperparameterSearch(
    **{'experiment_dir': '/absolute/path/to/parent/folder/your/experiments/should/be/saved',
       'experiment_name': 'experiment_griewank_1',
       'target_module_root_dir': '/absolute/path/to/root/dir/in/which/your/test_function/resides',
       'target_module_name': 'file_name_with_test_function_definition_(without_extension)',
       'target_function_name': 'name_of_function_inside_target_module',
       'parameter_definitions_root_dir_in': 'absolute/path/to/parent/folder/for/import',
       'parallelization': 'local_processes'})

hs.start_execution()
