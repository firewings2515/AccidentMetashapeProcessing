import os
import subprocess
import json

class MetashapeArguments:
    def __init__(self, project_path, project_name, data_root, usage='align'):
        self.project_path = project_path
        self.project_name = project_name
        self.data_root = data_root
        self.args = [] 

        self.usage = usage
        self.config_file = 'config.json'

        self.initial()
        if (os.path.exists(self.config_file)):
            print('Found config file. Using config structure.')
            self.initial_with_config()     

    def initial(self):
        # image folder name in data root path
        self.image_path = ["imageSet1", "imageEnv"]
        # match align each split_num photos. -1 means using all photos in folder.
        self.split_num = ["-1", "10"]
        # arpose file name in data root path
        self.ref_path = ["ARPose.txt", "ARPose.txt"]
        self.mask_path = ["",""]
        self.metashapePath = "C:/Program Files/Agisoft/Metashape Pro/metashape.exe"

    def initial_with_config(self):
        # Open and read the JSON file
        if (os.path.exists(self.config_file)):
            self.config = True
            with open(self.config_file, 'r') as file:
                data = json.load(file)
                if ('metashapeExePath' in data):
                    self.metashapePath = data['metashapeExePath']
                if ('image_path' in data):
                    self.image_path = data['image_path']
                if ('split_num' in data):
                    self.split_num = data['split_num']
                if ('ref_path' in data):
                    self.ref_path = data['ref_path']
                if ('mask_path' in data):
                    self.mask_path = data['mask_path']
    
    def check_args(self):
        usage_list = ['align', 'pointCloud']
        match_path_usage = ['align']
        if self.usage not in usage_list:
            raise Exception("Invalid usage")
        if not os.path.exists(self.project_path):
            print("project path not exists or invalid")
            raise Exception("Invalid project path")
        if self.image_path is None and self.usage == 'align':
            print("image_path required for align mode")
            raise Exception("Invalid image_path")

        if (self.usage in match_path_usage):
            if self.ref_path is not None and len(self.image_path) != len(self.ref_path):
                print("Image path, reference path and mask path should have the same length")
                raise Exception("Invalid script arguments")
            if self.split_num is not None and len(self.image_path) != len(self.split_num):
                print("Split num and image path must have the same length")
                raise Exception("Invalid script arguments")

    def build_args(self):
        self.check_args()
        self.set_init_args()
        if (self.usage == 'align'):
            self.args.append("--image_path")
            for path in self.image_path:
                self.args.append(os.path.join(self.data_root, path))
            
            self.args.append("--ref_path")
            for file in self.ref_path:
                self.args.append(os.path.join(self.data_root, file))

            self.args.append("--split_num")
            for num in self.split_num:
                self.args.append(num)
            
            self.args.append("--mask_path")
            for path in self.mask_path:
                self.args.append(os.path.join(self.data_root, path))
            # self.args.append("--copy")
        
        self.args.append("--usage")
        self.args.append(self.usage)
    
    def set_init_args(self):
        self.args = []
        self.args.append(self.metashapePath)
        self.args.append("-r")
        self.args.append("metashape_workflow.py")
        self.args.append("--output_path")
        self.args.append(self.project_path)

    def set_image_path(self, path_list):
        self.image_path = path_list

    def set_ref_list(self, ref_list):
        self.ref_path = ref_list
    
    def set_split_num(self, split_num):
        self.split_num = split_num

    def set_usage(self, usage):
        self.usage = usage
        
    def run(self):
        subprocess.run(args=self.args)
