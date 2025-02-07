import argparse
import os, time
import sys

import subprocess
from metashape_args import MetashapeArguments

def get_image_folder_name(root_path):
    return 'images_fps2'

# example for build list of folder data to reconstruction
# image_folder_Func: the function of image relative path
# arpose_name_Func: the function of arpose relative path 
def run_listDir(project_path, root_path, usage, image_folder_Func=None, arpose_name_Func=None, split_num='10'):
    dirs = os.listdir(root_path)
    image_path_list = []
    arpose_name_list = []
    split_num_list = []

    for i in range(len(dirs)):
        fullPath = os.path.join(root_path, dirs[i])
        if not os.path.isdir(fullPath):
            continue
        
        if (image_folder_Func is None):
            image_path_list.append(os.path.join(fullPath, 'images'))
        else:
            image_path_list.append(os.path.join(fullPath, image_folder_Func(dirs[i])))
        
        if (arpose_name_Func is None):
            arpose_name_list.append(os.path.join(fullPath,'ARposes_fixed.txt'))
        else:
            arpose_name_list.append(os.path.join(fullPath, arpose_name_Func(dirs[i])))
        
        split_num_list.append(split_num)

    runner = MetashapeArguments(project_path, "project.psx", root_path)
    runner.set_image_path(image_path_list)
    runner.set_ref_list(arpose_name_list)
    runner.set_split_num(split_num_list)
    runner.set_usage(usage)
    runner.build_args()
    runner.run()

# main function for build project reconstruction 
def run_project(project_path, data_root, usage='align'):
    runner = MetashapeArguments(project_path, "project.psx", data_root, usage)
    runner.build_args()
    runner.run()

def set_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_path', '-p', type=str)
    parser.add_argument('--root_path', '-r', type=str, required=True)
    parser.add_argument('--usage', '-u', type=str, default='align')
    return parser.parse_args()

def get_args(args):
    usage_list = ['align', 'pointCloud']
    if (args.usage not in usage_list):
        raise Exception("Invalid usage. Please input one of usage in list: ", usage_list)
    
    project_path = args.project_path
    root_path = args.root_path
    if (project_path is None):
        project_path = os.path.join(root_path, 'metashape')
    
    if (not os.path.exists(os.path.dirname(project_path))):
        raise Exception("project path invalid")
    if (not os.path.exists(project_path)):
        os.makedirs(project_path)
    
    return project_path, root_path, args.usage

if __name__ == '__main__':
    args = set_args()
    project_path ,root_path, usage = get_args(args)

    # TODO: listDir function run multiple project in given directory
    # TODO: listDir function run recorder case for list of image path
    # run_listDir(project_path, root_path, args.usage, image_folder_Func=get_image_folder_name)

	# run RealSceneProject function
    run_project(project_path, root_path, args.usage)
    