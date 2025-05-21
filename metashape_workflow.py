import utils
from metashape_utility import MetashapeUtility
from utils import *

def metashape_workflow(workflow, images_path_list, ref_path_list, mask_path_list, split_photo_num, copy_flag, unalign_name):
    # distribute all images according to split_photo_num (path_list -> image_list)
    photos_list, mask_list, ref_list = fetch_split_photo_list(images_path_list, ref_path_list, mask_path_list, split_photo_num)

    workflow.open_project()

    # start metashape workflow
    for i in range(len(photos_list)):
        if not workflow.add_photos(photos_list[i]):
            print("all photos already exist")
            continue

        workflow.import_reference(ref_list[i])

        workflow.import_mask(mask_list[i])

        workflow.match_photos()

    workflow.optimize_cameras()

    workflow.build_depthMaps()

    workflow.build_pointCloud()

    if (copy_flag):
        workflow.copy_chunk()

    workflow.save_unalign_log(unalign_name)

    workflow.end_time_list()

    workflow.save_log()

def metashape_match_align(workflow, images_path_list, ref_path_list, mask_path_list, split_photo_num, copy_flag, unalign_name):
     # distribute all images according to split_photo_num (path_list -> image_list)
    photos_list, mask_list, ref_list = fetch_split_photo_list(images_path_list, ref_path_list, mask_path_list, split_photo_num)

    workflow.open_project()

    # start metashape workflow
    for i in range(len(photos_list)):
        if not workflow.add_photos(photos_list[i]):
            print("all photos already exist")
            continue

        workflow.import_reference(ref_list[i])

        workflow.import_mask(mask_list[i])

        workflow.match_photos()

        workflow.optimize_cameras()
        
        if (copy_flag):
            workflow.copy_chunk()

    

    workflow.save_unalign_log(unalign_name)

    workflow.end_time_list()

    workflow.save_log()

def metashape_given_photos_match(project, photos_list, ref_list, mask_list, split_photo_num, copy_flag, unalign_name):

    project.open_project()

    # start metashape workflow
    if not project.add_photos(photos_list):
        print("all photos already exist")
        return

    project.import_reference(ref_list)

    project.import_mask(mask_list)

    project.match_photos()
        
    project.optimize_cameras()

    if (copy_flag):
        project.copy_chunk()

    project.save_unalign_log(unalign_name)

    project.end_time_list()

    project.save_log()

def metashape_build_pointcloud(project):
    project.open_project()

    project.build_depthMaps()

    project.build_pointCloud()

def metashape_error_log(project, error_name):
    project.open_project()

    project.save_camera_error(error_name)

def metashape_unalign_log(project, unalign_name):
    project.open_project()

    project.save_unalign_log(unalign_name)

def metashape_build_Texture(project, image_list_path):
    project.open_project()

    image_list = load_image_list(image_list_path)

    project.build_texture(image_list)

if __name__ == '__main__':
    args = set_args()

    # image mask ref split list length must be the same
    # list length more then one means incremental. 
    check_args(args)
    # print_log(args)

    # redirect metashape logs and separate from standard output
    redirect_stdout(args.output_path)

    metashape_proj = MetashapeUtility(args.project_name, args.output_path, args.pc_name)

    if (args.usage == 'complete'):
        mask_path_list, ref_path_list, split_photo_num = get_args_param(args)

        # new workflow or add photo workflow use same function. 
        # run complement incremental align if metashape project exist and already have chunk.
        metashape_workflow(metashape_proj, args.image_path, ref_path_list, mask_path_list, split_photo_num, args.copy, args.unalign_name)

    if (args.usage == 'photo_align'):
        mask_path_list, ref_path_list, split_photo_num = get_args_param(args)

        metashape_given_photos_match(metashape_proj, args.image_path, ref_path_list[0], mask_path_list[0], split_photo_num, args.copy, args.unalign_name)

    if (args.usage == 'align'):
        mask_path_list, ref_path_list, split_photo_num = get_args_param(args)

        metashape_match_align(metashape_proj, args.image_path, ref_path_list, mask_path_list, split_photo_num, args.copy, args.unalign_name)
    
    if (args.usage == 'error'):
        metashape_error_log(metashape_proj, args.error_name)

    if (args.usage == 'unalign'):
        metashape_unalign_log(metashape_proj, args.unalign_name)

    if (args.usage == 'pointCloud'):
        metashape_build_pointcloud(metashape_proj)
    
    if (args.usage == 'texture'):
        metashape_build_Texture(metashape_proj, args.image_list)
    