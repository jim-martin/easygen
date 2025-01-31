import json
import os
import copy
from modules import *
from image_modules import *
import pdb
import unicodedata
import argparse

TEMP_DIRECTORY = './cache'
HISTORY_PATH = os.path.join(TEMP_DIRECTORY, '.history')


parser = argparse.ArgumentParser(description='Run an easygen program.')
parser.add_argument('program', help="the file containing the easgen program.")
parser.add_argument('--clear_cache', help="Clear the cache", action='store_true')
    
# Inputs:
# - json description of the module
# - dictionary of history for caching
# Return 2 values:
# - Whether the module was run (could have not run because of caching)
# - The paths to files that were produced as outputs of the module (or none if the module wasn't ready)
def runModule(module_json, history = {}):
    module_json_copy = copy.deepcopy(module_json)
    if 'module' in module_json_copy:
        module = module_json_copy['module']
        ## Convert the json to a set of parameters to pass into a class of the same name as the module name
        ## Take the module name out
        del module_json_copy['module']
        ## Take out the x and y
        if 'x' in module_json_copy:
            del module_json_copy['x']
        if 'y' in module_json_copy:
            del module_json_copy['y']
        ## Take out the module name and id
        if 'name' in module_json_copy:
            del module_json_copy['name']
        if 'id' in module_json_copy:
            del module_json_copy['id']

        rest = str(module_json_copy)

        params = rest.replace('{', '').replace('}', '')
        #params = re.sub(r'u\'', '', params)
        #params = re.sub(r'\'', '', params)
        #params = re.sub(r': ', '=', params)
        p1 = re.compile(r'\'([0-9a-zA-Z\_]+)\':[\s]*(\'[\<\>\(\)0-9a-zA-Z\_\.\,\/\:\*\-\?\+\=\#\&\@\%\\\[\]\|\"\^ ]*\')')
        params = p1.sub(r"\1=\2", params)
        params = re.sub(r'\'True\'', 'True', params)
        params = re.sub(r'\'true\'', 'True', params)
        params = re.sub(r'\'False\'', 'False', params)
        params = re.sub(r'\'false\'', 'False', params)
        p2 = re.compile(r'\'([0-9]*[\.]*[0-9]+)\'')
        params = p2.sub(r'\1', params)
        ## Put the module name back on as class name
        evalString = module + '(' + convertHexToASCII(params) + ')'
        print("Module:", evalString)
        ## If everything went well, we can now evaluate the string and create a new class.
        module = eval(evalString)
        ## Do we need to run it?
        done_files = [] # The files that are in temp and generated by an identical process
        for key in history.keys():
            # key is a filename
            value = history[key] # string descriptor of the process that generated the file
            # Is the descriptor the same and does the file exist?
            if str(value) == str(module_json) and os.path.exists(key):
                # It is!
                done_files.append(key)
        output_files = module.output_files # These are the files we would expect to see
        # Check if all the output files are already done
        if len(set(output_files).difference(set(done_files))) == 0:
            # All the files we were going to output have been generated by an identical process
            print("Using cached data.")
            return False, output_files
        else:
            ## Run the class.
            if module.ready:
                print("Running...")
                module.run()
                print("Done.")
                return True, output_files
            else:
                print("Module not ready.")
                return False, None

def main(program_path):
    ### Make sure required directories exist
    if not os.path.exists(TEMP_DIRECTORY):
        os.makedirs(TEMP_DIRECTORY)

    ### Read the history file
    history = {}
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, 'r') as historyfile:
            history_text = historyfile.read().strip()
            if len(history_text) > 0:
                history = eval(history_text)
    
    ### Read in the program file
    data_text = ''
    data = None
    for line in open(program_path, "r"):
        data_text = data_text + line.strip()

    ### Convert to json dictionary
    data = json.loads(data_text)
    #data = byteify(data)

    use_caching = True # Should we use the caching system?

    ### Run each module
    if data is not None:
        print("Running", program_path)
        for d in data:
            # Run the module!
            executed, output_files = runModule(d, history if use_caching else {})
            # If the module ran and produced output_files then we shouldn't use caching anymore
            # If the module didn't run and output_files is None then it wasn't ready 
            #    and we are probably dead in the water
            # If the module didn't run and produced output_files then it is drawing from the cache, 
            #    keep doing so
            if (executed and output_files is not None) or (not executed and output_files is None):
                use_caching = False 
            # Update the history
            if output_files is not None:
                for file in output_files:
                    history[file] = d
        
            # Write the history to file
            with open(HISTORY_PATH, 'w') as historyfile:
                # Clean up the history file
                history_copy = copy.deepcopy(history)
                for file in history_copy.keys():
                    if not os.path.exists(file):
                        del history[file]
                # Now write
                historyfile.write(str(history))
    else:
        # No data to run
        print("Program is empty")

if __name__ == '__main__':
    args = parser.parse_args()
    if args.clear_cache:
        shutil.rmtree(TEMP_DIRECTORY)
    main(args.program)