import time
import sys
import yaml

from models import Model

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print('Incorrect usage, please use')
        print(f'python {sys.argv[0]} <model_file_name> <formula_file_name> [-draw]')
        quit()

    model_file = sys.argv[1]
    form_file = sys.argv[2]

    # Read model_file
    if model_file[-3:] == 'yml':
        with open(model_file, 'r') as file:
            yml_dict = yaml.safe_load(file)
        model = Model(yml_dict)
    else:
        print('Incorrect file type for model')
        quit()

    with open(form_file, 'r') as file:
        form = file.readline().replace('\n', '')
        worlds = file.readline().replace('\n', '').replace(' ', '')
        worlds = worlds.split(',')


    draw_flag = '-draw' in sys.argv
    
    if draw_flag:
        start_time = time.time()
        model.check(form, worlds, draw=True)
        end_time = time.time()
        print(f'Result calculated and drawn in {end_time-start_time} secs')
    else:
        start_time = time.time()
        result = model.check(form, worlds)
        end_time = time.time()
        print(f'Formula evaluates to {result}')
        print(f'Result calculated in {end_time - start_time} secs')