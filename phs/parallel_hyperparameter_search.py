import time
import os
import numpy as np
import pandas as pd
import json as js
import importlib
import sys
import pickle
from contextlib import redirect_stdout
from shutil import copy2

from phs import proxy
from phs import utils


class ParallelHyperparameterSearch:
    def __init__(self, **kwargs_dict):
        utils.print_section(header='ParallelHyperparameterSearch')
        if 'config_json_path' in kwargs_dict:
            with open(kwargs_dict['config_json_path']) as f:
                config_dict = js.load(f)
        else:
            config_dict = kwargs_dict

        self.experiment_name = config_dict['experiment_name']
        self.working_dir = config_dict['working_dir']
        self.custom_module_root_dir = config_dict['custom_module_root_dir']
        self.custom_module_name = config_dict['custom_module_name']
        self.custom_function_name = config_dict['custom_function_name']
        self.parameter_definitions_root_dir_in = config_dict['parameter_definitions_root_dir_in']
        self.parallelization = config_dict['parallelization']

        self.save_parameter_definitions = utils.set_default_value_to_optional_key(
            'save_parameter_definitions', True, config_dict)
        self.bayesian_wait_for_all = utils.set_default_value_to_optional_key(
            'bayesian_wait_for_all', False, config_dict)
        self.monitor_root_dir = utils.set_default_value_to_optional_key(
            'monitor_root_dir', None, config_dict)
        self.monitor_module_name = utils.set_default_value_to_optional_key(
            'monitor_module_name', None, config_dict)
        self.monitor_func_name_with_args = utils.set_default_value_to_optional_key(
            'monitor_func_name_with_args', {}, config_dict)
        self.provide_worker_path = utils.set_default_value_to_optional_key(
            'provide_worker_path', False, config_dict)

        for key, value in config_dict.items():
            print('\t{0:40}{1:}'.format(key, value))

        self.sub_future = []
        self.parameter_dict = {}
        self.parameter_dict_list = []
        self.result_frame = pd.DataFrame()
        self.additional_information_frame = pd.DataFrame()
        self.bayesian_register_dict = {}
        self.bayesian_register_dict_list = []
        self.bayesian_register_frame = pd.DataFrame()
        self.bayesian_options_bounds_low_dict = {}
        self.bayesian_options_bounds_low_dict_list = []
        self.bayesian_options_bounds_low_frame = pd.DataFrame()
        self.bayesian_options_bounds_high_dict = {}
        self.bayesian_options_bounds_high_dict_list = []
        self.bayesian_options_bounds_high_frame = pd.DataFrame()
        self.bayesian_options_round_digits_dict = {}
        self.bayesian_options_round_digits_dict_list = []
        self.bayesian_options_round_digits_frame = pd.DataFrame()
        self.parameter_string_list = []
        self.parameter_index_list = []
        self.experiment_dir = self.working_dir + '/' + self.experiment_name
        self.result_path = self.experiment_dir + '/results'
        self.parameter_definitions_root_dir_out = self.experiment_dir + '/parameter_definitions'
        self.result_file_path = self.result_path + '/result_frame.csv'
        self.lock_result_path = self.result_path + '/LOCK'
        self.additional_information_file_path = self.result_path + '/additional_information_frame.csv'
        self.source_code = self.experiment_dir + '/source_code_func'
        self.model_preview_path = self.experiment_dir + '/model_preview'

        self.parameter_frame_name = '/parameter_frame'
        self.bayesian_register_frame_name = '/bayesian_register_frame'
        self.bayesian_options_bounds_low_frame_name = '/bayesian_options_bounds_low_frame'
        self.bayesian_options_bounds_high_frame_name = '/bayesian_options_bounds_high_frame'
        self.bayesian_options_round_digits_name = '/bayesian_options_round_digits_frame'
        self.data_types_ordered_list_name = '/data_types_ordered_list'
        self.data_types_additional_information_dict_name = '/data_types_additional_information_dict'

        self.path_in_to_parameter_frame = self.parameter_definitions_root_dir_in + self.parameter_frame_name
        self.path_in_to_bayesian_register_frame = self.parameter_definitions_root_dir_in + \
            self.bayesian_register_frame_name
        self.path_in_to_bayesian_options_bounds_low_frame = self.parameter_definitions_root_dir_in + \
            self.bayesian_options_bounds_low_frame_name
        self.path_in_to_bayesian_options_bounds_high_frame = self.parameter_definitions_root_dir_in + \
            self.bayesian_options_bounds_high_frame_name
        self.path_in_to_bayesian_options_round_digits_frame = self.parameter_definitions_root_dir_in + \
            self.bayesian_options_round_digits_name
        self.path_in_to_data_types_ordered_list = self.parameter_definitions_root_dir_in + \
            self.data_types_ordered_list_name

        self.path_out_to_parameter_frame = self.parameter_definitions_root_dir_out + self.parameter_frame_name
        self.path_out_to_bayesian_register_frame = self.parameter_definitions_root_dir_out + \
            self.bayesian_register_frame_name
        self.path_out_to_bayesian_options_bounds_low_frame = self.parameter_definitions_root_dir_out + \
            self.bayesian_options_bounds_low_frame_name
        self.path_out_to_bayesian_options_bounds_high_frame = self.parameter_definitions_root_dir_out + \
            self.bayesian_options_bounds_high_frame_name
        self.path_out_to_bayesian_options_round_digits_frame = self.parameter_definitions_root_dir_out + \
            self.bayesian_options_round_digits_name
        self.path_out_to_data_types_ordered_list = self.parameter_definitions_root_dir_out + \
            self.data_types_ordered_list_name
        self.path_out_to_data_types_additional_information_dict = self.parameter_definitions_root_dir_out + \
            self.data_types_additional_information_dict_name

        self.result_col_name = 'result'
        self.symbol_for_best = '+'
        self.expression_data_type_flag = 'expr'
        self.append_additional_information_init = False

        if os.path.exists(self.working_dir) and os.path.isdir(self.working_dir):
            if os.path.exists(self.experiment_dir) and os.path.isdir(self.experiment_dir):
                raise ValueError('directory ' + self.experiment_dir +
                                 ' already exists. Please choose a different experiment name.')
            else:
                os.mkdir(self.experiment_dir)
                os.mkdir(self.result_path)
                os.mkdir(self.parameter_definitions_root_dir_out)
                os.mkdir(self.source_code)

            if self.monitor_root_dir is not None:
                self.monitor_path = self.experiment_dir + '/monitor'
                os.mkdir(self.monitor_path)

            if self.provide_worker_path:
                self.worker_save_path_root = self.experiment_dir + '/worker_out'
                os.mkdir(self.worker_save_path_root)
            else:
                self.worker_save_path_root = False

        else:
            raise ValueError('directory ' + self.working_dir + ' doesn\'t exist.')

        self.parameter_frame = pd.read_pickle(self.path_in_to_parameter_frame + '.pkl')
        self.bayesian_register_frame = pd.read_pickle(
            self.path_in_to_bayesian_register_frame + '.pkl')
        self.bayesian_options_bounds_low_frame = pd.read_pickle(
            self.path_in_to_bayesian_options_bounds_low_frame + '.pkl')
        self.bayesian_options_bounds_high_frame = pd.read_pickle(
            self.path_in_to_bayesian_options_bounds_high_frame + '.pkl')
        self.bayesian_options_round_digits_frame = pd.read_pickle(
            self.path_in_to_bayesian_options_round_digits_frame + '.pkl')
        with open(self.path_in_to_data_types_ordered_list + '.pkl', 'rb') as f:
            self.data_types_ordered_list = pickle.load(f)

        copy2(self.custom_module_root_dir + '/' + self.custom_module_name +
              '.py', self.source_code + '/' + self.custom_module_name + '.py')

        sys.path.append(self.custom_module_root_dir)
        self.custom_module = importlib.import_module(self.custom_module_name)
        self.custom_function = getattr(self.custom_module, self.custom_function_name)

        if self.monitor_root_dir:
            sys.path.append(self.monitor_root_dir)
        if self.monitor_module_name:
            self.monitor_module = importlib.import_module(self.monitor_module_name)

        self.monitor_functions_dict = {}
        for func_name in self.monitor_func_name_with_args:
            self.monitor_functions_dict[func_name] = getattr(self.monitor_module, func_name)

    def show_parameter_set_dtypes(self):
        print(self.parameter_frame.dtypes)

    def show_parameter_set(self):
        print(self.parameter_frame)

    def show_bayesian_options_bounds_low_frame(self):
        print('bayesian_options_bounds_low_frame')
        print(self.bayesian_options_bounds_low_frame)

    def show_bayesian_options_bounds_high_frame(self):
        print('bayesian_options_bounds_high_frame')
        print(self.bayesian_options_bounds_high_frame)

    def show_bayesian_options_round_digits_frame(self):
        print('bayesian_options_round_digits_frame')
        print(self.bayesian_options_round_digits_frame)

    def create_parameter_string_list(self):
        self.parameter_string_list = []
        list_of_dicts = self.parameter_frame.to_dict(orient='records')
        for dict_i in list_of_dicts:
            for key in dict_i:
                dict_i[key] = dict_i[key].item()
            string = js.dumps(dict_i, separators=['\n', '='])
            string = string.replace('"', "")
            string = string.strip('{}')
            self.parameter_string_list.append(string)
        return self.parameter_string_list

    def show_model_preview(self, preview_function_name):
        os.mkdir(self.model_preview_path)
        with open(self.model_preview_path + '/model_preview.txt', 'w') as f:
            with redirect_stdout(f):
                self.model_preview_out(preview_function_name)
        self.model_preview_out(preview_function_name)

    def model_preview_out(self, preview_function_name):
        self.preview_function_name = preview_function_name
        self.loaded_preview_function = getattr(self.custom_module, self.preview_function_name)

        parameter_string_list_preview = self.create_parameter_string_list()
        parameter_index_list_preview = self.parameter_frame.index.values.tolist()
        list_of_parameter_dicts_preview = self.parameter_frame.astype(
            object).to_dict(orient='records')
        for i in parameter_index_list_preview:
            parameter_dict_i = list_of_parameter_dicts_preview[i]
            string = js.dumps(parameter_dict_i, separators=['\n', '='])
            # string = string.strip('{}')
            string = string[1:-1]
            for key in parameter_dict_i:
                string = string.replace("\"" + key + "\"", key)
            print('\nparameter set ' + str(i) + ':')
            self.loaded_preview_function(string)

    def save_parameter_definitions_func(self):
        if True:
            self.parameter_frame.to_pickle(self.path_out_to_parameter_frame + '.pkl')
            with open(self.path_out_to_parameter_frame + '.txt', 'w') as f:
                f.write(self.parameter_frame.to_string())
            self.parameter_frame.to_csv(self.path_out_to_parameter_frame +
                                        '.csv', sep='\t', index=True, header=True)

            self.bayesian_register_frame.to_pickle(
                self.path_out_to_bayesian_register_frame + '.pkl')
            with open(self.path_out_to_bayesian_register_frame + '.txt', 'w') as f:
                f.write(self.bayesian_register_frame.to_string())
            self.bayesian_options_bounds_low_frame.to_pickle(
                self.path_out_to_bayesian_options_bounds_low_frame + '.pkl')
            with open(self.path_out_to_bayesian_options_bounds_low_frame + '.txt', 'w') as f:
                f.write(self.bayesian_options_bounds_low_frame.to_string())
            self.bayesian_options_bounds_high_frame.to_pickle(
                self.path_out_to_bayesian_options_bounds_high_frame + '.pkl')
            with open(self.path_out_to_bayesian_options_bounds_high_frame + '.txt', 'w') as f:
                f.write(self.bayesian_options_bounds_high_frame.to_string())
            self.bayesian_options_round_digits_frame.to_pickle(
                self.path_out_to_bayesian_options_round_digits_frame + '.pkl')
            with open(self.path_out_to_bayesian_options_round_digits_frame + '.txt', 'w') as f:
                f.write(self.bayesian_options_round_digits_frame.to_string())
            with open(self.path_out_to_data_types_ordered_list + '.pkl', 'wb') as f:
                pickle.dump(self.data_types_ordered_list, f)
            with open(self.path_out_to_data_types_ordered_list + '.txt', 'w') as f:
                f.write(str(self.data_types_ordered_list))

    def initialize_result_file(self):
        header_list = list(self.parameter_frame.columns.values)
        header_string = 'index'
        for i in header_list:
            header_string = header_string + ',' + str(i)
        header_string = header_string + ',' + self.result_col_name + '\n'
        with open(self.result_file_path, 'w') as f:
            f.write(header_string)

    def start_execution(self):
        utils.print_subsection(header='start execution')
        print('\tobserve arrival of results with:\t\'watch -n 1 "(head -n 1; tail -n 10) < %s\"\'' %
              (self.result_file_path))
        if self.save_parameter_definitions:
            self.save_parameter_definitions_func()
        self.initialize_result_file()

        # input('\tPress Enter to start execution...')

        if self.parallelization == 'processes':
            from concurrent.futures import ProcessPoolExecutor as PoolExecutor
            from concurrent.futures import wait, as_completed
            with PoolExecutor(max_workers=4) as executor:
                self.start_execution_kernel(executor, wait, as_completed)
                self.as_completed_functions(as_completed)

        elif self.parallelization == 'mpi':
            from mpi4py.futures import MPIPoolExecutor as PoolExecutor
            from mpi4py.futures import wait, as_completed
            with PoolExecutor(max_workers=2) as executor:
                self.start_mpi_execution_kernel(executor, wait, as_completed)
                self.as_completed_functions(as_completed)

        elif self.parallelization == 'dask':
            from dask.distributed import Client, progress, as_completed, scheduler, wait
            DASK_MASTER_IP = os.environ['DASK_MASTER_IP']
            DASK_MASTER_PORT = os.environ['DASK_MASTER_PORT']
            with Client(DASK_MASTER_IP + ':' + DASK_MASTER_PORT, timeout='50s') as client:
                # client.upload_file(self.repository_root_dir + '/parallel_hyperparameter_search/phs/utils.py')
                # client.upload_file(self.repository_root_dir + '/parallel_hyperparameter_search/phs/bayes.py')
                # client.upload_file(self.repository_root_dir + '/parallel_hyperparameter_search/phs/proxy.py')
                # client.upload_file(self.custom_module_root_dir + '/' +
                # self.custom_module_name + '.py')
                self.start_execution_kernel(client, wait, as_completed)
                self.as_completed_functions(as_completed)
        return 1

    def start_execution_kernel(self, executor, wait, as_completed):
        parameter_index_list = self.parameter_frame.index.values.tolist()
        paths = {'lock_result_path': self.lock_result_path,
                 'result_file_path': self.result_file_path}

        list_of_parameter_dicts = self.parameter_frame.to_dict(orient='records')
        list_of_bayesian_register_dicts = self.bayesian_register_frame.to_dict(
            orient='records')
        list_of_bayesian_options_bounds_low_dicts = self.bayesian_options_bounds_low_frame.to_dict(
            orient='records')
        list_of_bayesian_options_bounds_high_dicts = self.bayesian_options_bounds_high_frame.to_dict(
            orient='records')
        list_of_bayesian_options_round_digits_dicts = self.bayesian_options_round_digits_frame.to_dict(
            orient='records')
        for i in parameter_index_list:
            parameter_dict_i = list_of_parameter_dicts[i]
            bayesian_register_dict_i = list_of_bayesian_register_dicts[i]
            auxiliary_information = {'worker_save_path_root': self.worker_save_path_root}
            if not any(bayesian_register_dict_i.values()):
                self.sub_future.append(executor.submit(proxy.proxy_function,
                                                       self.parallelization,
                                                       self.custom_function,
                                                       arg=parameter_dict_i,
                                                       index=i,
                                                       data_types_ordered_list=self.data_types_ordered_list,
                                                       expression_data_type_flag=self.expression_data_type_flag,
                                                       auxiliary_information=auxiliary_information))
            else:
                bayesian_register_dict_i = list_of_bayesian_register_dicts[i]
                bayesian_options_bounds_low_dict_i = list_of_bayesian_options_bounds_low_dicts[i]
                bayesian_options_bounds_high_dict_i = list_of_bayesian_options_bounds_high_dicts[i]
                bayesian_options_round_digits_dict_i = list_of_bayesian_options_round_digits_dicts[i]
                self.sub_future.append(executor.submit(proxy.proxy_function,
                                                       self.parallelization,
                                                       self.custom_function,
                                                       arg=parameter_dict_i,
                                                       index=i,
                                                       data_types_ordered_list=self.data_types_ordered_list,
                                                       expression_data_type_flag=self.expression_data_type_flag,
                                                       auxiliary_information=auxiliary_information,
                                                       with_bayesian=True,
                                                       paths=paths,
                                                       result_col_name=self.result_col_name,
                                                       bayesian_wait_for_all=self.bayesian_wait_for_all,
                                                       bayesian_register_dict=bayesian_register_dict_i,
                                                       bayesian_options_bounds_low_dict=bayesian_options_bounds_low_dict_i,
                                                       bayesian_options_bounds_high_dict=bayesian_options_bounds_high_dict_i,
                                                       bayesian_options_round_digits_dict=bayesian_options_round_digits_dict_i))
        return 1

    def start_mpi_execution_kernel(self, executor, wait, as_completed):
        parameter_string_list = self.create_parameter_string_list()
        parameter_index_list = self.parameter_frame.index.values.tolist()
        paths = {'lock_result_path': self.lock_result_path, 'result_file_path': self.result_file_path, 'path_to_bayesian_options_bounds_low_frame': self.path_to_bayesian_options_bounds_low_frame,
                 'path_to_bayesian_options_bounds_high_frame': self.path_to_bayesian_options_bounds_high_frame, 'path_to_bayesian_options_round_digits_frame': self.path_to_bayesian_options_round_digits_frame}

        list_of_parameter_dicts = self.parameter_frame.astype(object).to_dict(orient='records')
        for i in parameter_index_list:
            parameter_dict_i = list_of_parameter_dicts[i]
            auxiliary_information = {'save_path': self.worker_save_path_root, 'parameter_index': i}
            if self.bayesian_placeholder_phrase not in parameter_dict_i.values():
                self.sub_future.append(executor.submit(proxy.proxy_function, self.parallelization,
                                                       self.custom_function, arg=parameter_dict_i, index=i, auxiliary_information=auxiliary_information))
            else:
                self.sub_future.append(executor.submit(proxy.proxy_function, self.parallelization, self.custom_function, arg=parameter_dict_i, index=i, auxiliary_information=auxiliary_information,
                                                       with_bayesian=True, bayesian_placeholder_phrase=self.bayesian_placeholder_phrase, paths=paths, data_types_ordered=self.data_types_ordered))
        return 1

    def start_dask_execution_kernel(self, executor, wait, as_completed):
        parameter_string_list = self.create_parameter_string_list()
        parameter_index_list = self.parameter_frame.index.values.tolist()
        paths = {'lock_result_path': self.lock_result_path, 'result_file_path': self.result_file_path, 'path_to_bayesian_options_bounds_low_frame': self.path_to_bayesian_options_bounds_low_frame,
                 'path_to_bayesian_options_bounds_high_frame': self.path_to_bayesian_options_bounds_high_frame, 'path_to_bayesian_options_round_digits_frame': self.path_to_bayesian_options_round_digits_frame}

        list_of_parameter_dicts = self.parameter_frame.astype(object).to_dict(orient='records')
        for i in parameter_index_list:
            parameter_dict_i = list_of_parameter_dicts[i]
            auxiliary_information = {'save_path': self.worker_save_path_root, 'parameter_index': i}
            if self.bayesian_placeholder_phrase not in parameter_dict_i.values():
                self.sub_future.append(executor.submit(proxy.proxy_function, self.parallelization, self.custom_function,
                                                       arg=parameter_dict_i, index=i, auxiliary_information=auxiliary_information, priority=10, fifo_timeout='0ms'))
            else:
                self.sub_future.append(executor.submit(proxy.proxy_function, self.parallelization, self.custom_function, arg=parameter_dict_i, index=i, auxiliary_information=auxiliary_information,
                                                       with_bayesian=True, bayesian_placeholder_phrase=self.bayesian_placeholder_phrase, paths=paths, data_types_ordered=self.data_types_ordered, priority=-10, fifo_timeout='0ms'))
        return 1

    def as_completed_functions(self, as_completed):
        print('', end='\n')
        for count_finished, f in enumerate(as_completed(self.sub_future), 1):
            print('===>\tfinished tasks:\t{0:>6} of {1:>6}' .format(
                count_finished, len(self.sub_future)), end='\r')
            self.append_result(f)
            self.append_additional_information(f)
            self.monitor_functions()
        print('\n')
        return 1

    def append_result(self, future):
        start_time = time.time()

        index = (future.result())[0]
        current_result_dict = self.parameter_frame.iloc[[index]].to_dict(orient='list')
        if (future.result())[5] is not None:
            bayesian_replacement_dict = (future.result())[5]
            for col_name in bayesian_replacement_dict:
                current_result_dict[col_name] = bayesian_replacement_dict[col_name]
        current_result_dict[self.result_col_name] = (future.result())[1]
        current_result_df = pd.DataFrame(current_result_dict, index=[index])

        self.result_frame = self.result_frame.append(
            current_result_df, ignore_index=False, verify_integrity=False)

        # self.result_frame = self.result_frame.applymap(
        #     lambda x: round(x, 4) if isinstance(x, (int, float)) else x)
        while True:
            try:
                os.mkdir(self.lock_result_path)
                break
            except OSError:
                # print('write locked')
                time.sleep(0.5)
                continue

        with open(self.result_file_path, 'a') as f:
            current_result_df.to_csv(f, header=False, index=True)

        if os.path.exists(self.lock_result_path) and os.path.isdir(self.lock_result_path):
            os.rmdir(self.lock_result_path)

        # print('\nrefresh log:\t%.3f' % (time.time()-start_time), end='\n')
        return 1

    def append_additional_information(self, future):
        index = (future.result())[0]
        current_additional_information_dict = {}
        current_additional_information_dict['started'] = (future.result())[2]
        current_additional_information_dict['ended'] = (future.result())[3]
        current_additional_information_dict['execution time'] = (future.result())[
            3] - (future.result())[2]
        current_additional_information_dict['worker'] = (future.result())[4]
        current_additional_information_dict['state'] = (future._state)
        current_additional_information_df = pd.DataFrame(
            current_additional_information_dict, index=[index])
        self.additional_information_frame = self.additional_information_frame.append(
            current_additional_information_df, ignore_index=False, verify_integrity=False)

        if not self.append_additional_information_init:
            with open(self.additional_information_file_path, 'w') as f:
                current_additional_information_df.to_csv(f, header=True, index=True)

            self.data_types_additional_information_dict = {}
            for key, value in current_additional_information_dict.items():
                self.data_types_additional_information_dict[key] = type(value)
            with open(self.path_out_to_data_types_additional_information_dict + '.pkl', 'wb') as f:
                pickle.dump(self.data_types_additional_information_dict, f)
            with open(self.path_out_to_data_types_additional_information_dict + '.txt', 'w') as f:
                f.write(str(self.data_types_additional_information_dict))

            self.append_additional_information_init = True
        else:
            with open(self.additional_information_file_path, 'a') as f:
                current_additional_information_df.to_csv(f, header=False, index=True)

        return 1

    def monitor_functions(self):
        start_time = time.time()
        for monitor_function_string in self.monitor_func_name_with_args:
            kwargs_dict = self.monitor_func_name_with_args[monitor_function_string]
            kwargs_dict['path_out'] = self.monitor_path
            kwargs_dict['result_frame'] = self.result_frame
            kwargs_dict['additional_information_frame'] = self.additional_information_frame
            kwargs_dict['path_to_bayesian_register_frame'] = self.path_out_to_bayesian_register_frame
            self.monitor_functions_dict[monitor_function_string](**kwargs_dict)

        # print('refresh plot:\t%.3f' %(time.time()-start_time), end='\t')
        return 1
