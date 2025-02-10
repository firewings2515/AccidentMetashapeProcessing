import argparse
import os, time
import sys
# use for split filename and extension
import pathlib
import csv

# code reference:
# https://stackoverflow.com/questions/5081657/how-do-i-prevent-a-c-shared-library-to-print-on-stdout-in-python/17954769#17954769
# responses from Dietrich Epp
def redirect_stdout(path):
    print("Redirecting stdout")
    sys.stdout.flush() # <--- important when redirecting to files
    newstdout = os.dup(1)
    # devnull = os.open(os.devnull, os.O_WRONLY)
    cstdout = os.open(path + '/metashape_log.txt', os.O_RDWR|os.O_CREAT)
    os.dup2(cstdout, 1)
    os.close(cstdout)
    sys.stdout = os.fdopen(newstdout, 'w')

def set_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image_path', '-i', type=str, nargs='*')
    parser.add_argument('--ref_path', '-r', type=str, nargs='*')
    parser.add_argument('--mask_path', '-m', type=str, nargs='*')
    parser.add_argument('--split_num', '-s', type=str, nargs='*')
    parser.add_argument('--output_path', '-o', type=str, required=True)
    parser.add_argument('--project_name', '-p', type=str, default='project.psx')
    parser.add_argument('--pc_name', '-pc', type=str, default='point_cloud.xyz')
    # usage: full, add
    parser.add_argument('--usage', '-u', type=str, default='align')
    parser.add_argument('--error_name', '-er', type=str, default='error.txt')
    parser.add_argument('--unalign_name', '-un', type=str, default='unalign.txt')
    parser.add_argument("--copy", default=False, action="store_true")
    return parser.parse_args()

def check_args(args):
    usage = ['align', 'error', 'unalign', 'pointCloud', 'complete', 'photo_align']
    match_path_usage = ['align', 'complete']
    if args.usage not in usage:
        raise Exception("Invalid usage")
    if not os.path.exists(args.output_path):
        print_log(args)
        print("project path not exists or invalid")
        raise Exception("Invalid project path")
    if args.image_path is None and args.usage == 'align':
        print_log(args)
        print("image_path required for align mode")
        raise Exception("Invalid image_path")

    if (args.usage in match_path_usage):
        if args.ref_path is not None and len(args.image_path) != len(args.ref_path):
            print_log(args)
            print("Image path, reference path and mask path should have the same length")
            raise Exception("Invalid script arguments")
        if args.mask_path is not None and len(args.image_path) != len(args.mask_path):
            print_log(args)
            print("Image path, reference path and mask path should have the same length")
            raise Exception("Invalid script arguments")
        if args.split_num is not None and len(args.image_path) != len(args.split_num):
            print_log(args)
            print("Split num and image path must have the same length")
            raise Exception("Invalid script arguments")

def get_args_param(args):
    mask_path_list = []
    ref_path_list = []
    split_photo_num = []

    if args.ref_path is None:
        ref_path_list = ['' for i in range(len(args.image_path))]
    else:
        ref_path_list = args.ref_path
    if args.mask_path is None:
        mask_path_list = ['' for i in range(len(args.image_path))]
    else:
        mask_path_list = args.mask_path
    if args.split_num is None:
        split_photo_num = [-1 for i in range(len(args.image_path))]
    else:
        split_photo_num = args.split_num
    
    return mask_path_list, ref_path_list, split_photo_num

def print_log(args):
    for i in range(len(args.image_path)):
        print('image path: %s' % args.image_path[i])
    for i in range(len(args.ref_path)):
        print('ref_path: %s' % args.ref_path[i])
    for i in range(len(args.mask_path)):
        print('mask path: %s' % args.mask_path[i])
    for i in range(len(args.split_num)):
        print('split num: %s' % args.split_num[i])

def fetch_split_photo_list(images_path_list, ref_path_list, mask_path_list, split_photo_num):
    photos_list = []
    mask_list = []
    ref_list = []
    for i in range(len(images_path_list)):
        Photos, _ = find_files(images_path_list[i], [".jpg", ".jpeg", ".tif", ".tiff"])
        n = int(split_photo_num[i])
        if (n == -1):
            photos_list.append(Photos)
            mask_list.append(mask_path_list[i])
            ref_list.append(ref_path_list[i])
        else:
            photo_split = [Photos[j:j + n] for j in range(0, len(Photos), n)]
            # define a mask list with same size as photo_split. assign same mask path to each element
            mask_split = [mask_path_list[i] for j in range(len(photo_split))]
            ref_split = [ref_path_list[i] for j in range(len(photo_split))]
            photos_list.extend(photo_split)
            mask_list.extend(mask_split)
            ref_list.extend(ref_split)
    return photos_list, mask_list, ref_list

# image_file_list is a list of path
# filename_list is a list of filename without extension
def find_files(folder, types):
    image_file_list = []
    filename_list = []
    for entry in os.scandir(folder):
        if entry.is_file() and os.path.splitext(entry.name)[1].lower() in types:
            image_file_list.append(entry.path)
            filename = pathlib.Path(entry.name).stem
            filename_list.append(filename)
    return image_file_list, filename_list