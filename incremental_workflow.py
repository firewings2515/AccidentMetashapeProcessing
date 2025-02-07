# This script in modify from git source below
# https://github.com/agisoft-llc/metashape-scripts/tree/master/src

import Metashape
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

def get_list_diff(list1, list2):
    diff1 = [item for item in list1 if item not in list2]
    diff2 = [item for item in list2 if item not in list1]

    diff = diff1 + diff2

    return diff
def find_files(folder, types):
    image_file_list = []
    filename_list = []
    for entry in os.scandir(folder):
        if entry.is_file() and os.path.splitext(entry.name)[1].lower() in types:
            image_file_list.append(entry.path)
            filename = pathlib.Path(entry.name).stem
            filename_list.append(filename)
    return image_file_list, filename_list

def workflow_incremental_each_photoMask(images_path_list, ref_path_list, mask_path_list, split_photo_num, output_folder, project_name = 'project.psx'):
    # Checking compatibility
    compatible_major_version = "2.1"
    found_major_version = ".".join(Metashape.app.version.split('.')[:2])
    if found_major_version != compatible_major_version:
        raise Exception("Incompatible Metashape version: {} != {}".format(found_major_version, compatible_major_version))

    Metashape.app.gpu_mask = 2**len(Metashape.app.enumGPUDevices()) - 1
    if Metashape.app.gpu_mask:
        Metashape.app.cpu_enable = False 
    else:
        Metashape.app.cpu_enable = True
    # incremental add 10 photos
    doc = Metashape.Document()
    if os.path.isfile(output_folder + project_name):
        doc.open(output_folder + project_name)
    else:
        doc.save(output_folder + project_name)
    
    doc.read_only = False
    chunk = doc.addChunk()
    total_copy_chunk_time = 0
    copy_flag = False

    def find_files(folder, types):
        image_file_list = []
        filename_list = []
        for entry in os.scandir(folder):
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in types:
                image_file_list.append(entry.path)
                filename = pathlib.Path(entry.name).stem
                filename_list.append(filename)
        return image_file_list, filename_list
    
    # get all photos
    photos_list = []
    mask_list = []
    ref_list = []
    all_cameras = []
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

    start_time = time.perf_counter()
    total_copy_chunk_time = 0
    copy_flag = False
    
    all_time_list = []
    # split to 10 photos each time
    for i in range(len(photos_list)):
        time_list = []

        # add photo and give mask to those new photos
        # maybe can get camera after add photo by get the end of n cameras
        start_import_photo_time = time.perf_counter()
        print('import photos ...')
        time_list.insert(0, len(photos_list[i]))
        chunk.addPhotos(photos_list[i])
        doc.save()
        end_import_photo_time = time.perf_counter()
        print('import photos time: %f s' % (end_import_photo_time - start_import_photo_time))
        time_list.append(end_import_photo_time - start_import_photo_time)

        start_import_refernce_time = time.perf_counter()
        # check if ref file txt exist and import
        if ref_list != None and os.path.exists(ref_list[i]):
            print('import reference file ' + ref_list[i] + ' ...')
            chunk.importReference(ref_list[i], format=Metashape.ReferenceFormatCSV, delimiter=',', columns='nxyzabc', create_markers=False)
            doc.save()
            end_import_refernce_time = time.perf_counter()
            print('import reference time: %f s' % (end_import_refernce_time - start_import_refernce_time))
            time_list.append(end_import_refernce_time - start_import_refernce_time)
        else:
            time_list.append(0)
        
        start_import_mask_time = time.perf_counter()
        if mask_list != None and os.path.exists(mask_list[i]):
            # create a new list append the camera which is new in chunk.cameras not in all_cameras 
            new_cameras = [camera for camera in chunk.cameras if camera not in all_cameras]
            mask_files, mask_name_list = find_files(mask_list[i], [".jpg", ".jpeg", ".tif", ".tiff"])
            chunk.generateMasks(path=(mask_list[i] + '/{filename}_mask.png'), masking_mode=Metashape.MaskingModeFile, mask_operation=Metashape.MaskOperationReplacement, cameras=new_cameras)
            doc.save()
            end_import_mask_time = time.perf_counter()
            print('import mask time: %f s' % (end_import_mask_time - start_import_mask_time))
            time_list.append(end_import_mask_time - start_import_mask_time)
        else:
            time_list.append(0)

        unaligned_cameras = [camera for camera in chunk.cameras if not camera.transform]
        start_match_time = time.perf_counter()
        print('Start matchPhotos...')
        print('num of cameras: ', len(chunk.cameras))
        print('Unaligned cameras: ' + str(len(unaligned_cameras)))
        chunk.matchPhotos(cameras=unaligned_cameras, keypoint_limit = 10000, tiepoint_limit = 4000, keep_keypoints=True, 
                generic_preselection = True, reset_matches=False, 
                filter_stationary_points=False, guided_matching=True)
        doc.save()
        end_match_time = time.perf_counter()
        print('matchPhotos time: %f s' % (end_match_time - start_match_time))
        time_list.append(end_match_time - start_match_time)

        start_align_time = time.perf_counter()
        print('Start alignCameras...')
        chunk.alignCameras(cameras=unaligned_cameras, adaptive_fitting=True, reset_alignment=False)
        doc.save()
        end_align_time = time.perf_counter()
        print('alignCameras time: %f s' % (end_align_time - start_align_time))
        time_list.append(end_align_time - start_align_time)

        if (copy_flag):
            start_copychunk_time = time.perf_counter()
            chunk = chunk.copy(keypoints=True)
            doc.save()
            end_copychunk_time = time.perf_counter()
            total_copy_chunk_time += (end_copychunk_time - start_copychunk_time)
            print('copy chunk time: %f s' % (end_copychunk_time - start_copychunk_time))
            time_list.append(end_copychunk_time - start_copychunk_time)
        
        all_time_list.append(time_list)
        all_cameras = chunk.cameras

    start_optimizeCamera_time = time.perf_counter()
    chunk.optimizeCameras(adaptive_fitting=True)
    chunk.resetRegion()
    doc.save()
    end_optimizeCamera_time = time.perf_counter()
    print('optimizeCameras time: %f s' % (end_optimizeCamera_time - start_optimizeCamera_time))
    all_time_list.append([end_optimizeCamera_time - start_optimizeCamera_time])

    start_pointCloud_time = time.perf_counter()
    chunk.buildDepthMaps(downscale = 16, filter_mode = Metashape.MildFiltering)
    doc.save()
    chunk.buildPointCloud()
    doc.save()
    if chunk.point_cloud:
        chunk.exportPointCloud(output_folder + '/point_cloud.xyz', source_data = Metashape.PointCloudData)

    end_pointCloud_time = time.perf_counter()
    print('Build Point cloud time: %f s' % (end_pointCloud_time - start_pointCloud_time))
    all_time_list.append([end_pointCloud_time - start_pointCloud_time])

    end_time = time.perf_counter()
    if (copy_flag):
        print('total copy chunk time: %f s' % (total_copy_chunk_time))
        all_time_list.append([total_copy_chunk_time])
    
    print('total process time: %f s' % (end_time - start_time))
    all_time_list.append([end_time - start_time])

    # output csv
    with open(output_folder + '/result.csv', 'w', newline='', encoding='utf-8') as f:
        write = csv.writer(f)
        write.writerows(all_time_list)

def incremental_addPhoto(images_list, ref_path, mask_path, output_folder, project_name = 'project.psx'):
    # Checking compatibility
    compatible_major_version = "2.1"
    found_major_version = ".".join(Metashape.app.version.split('.')[:2])
    if found_major_version != compatible_major_version:
        raise Exception("Incompatible Metashape version: {} != {}".format(found_major_version, compatible_major_version))

    Metashape.app.gpu_mask = 2**len(Metashape.app.enumGPUDevices()) - 1
    if Metashape.app.gpu_mask:
        Metashape.app.cpu_enable = False 
    else:
        Metashape.app.cpu_enable = True
    # incremental add 10 photos
    doc = Metashape.Document()
    if os.path.isfile(output_folder + project_name):
        doc.open(output_folder + project_name)
    else:
        doc.save(output_folder + project_name)
    
    doc.read_only = False
    if (len(doc.chunks) == 0):
        chunk = doc.addChunk()
    else:
        chunk = doc.chunks[0]
    total_copy_chunk_time = 0
    copy_flag = False
    
    camera_paths = [camera.photo.path for camera in chunk.cameras]

    # record the number of photos
    all_cameras = chunk.cameras
    images_list_fixed = get_list_diff(images_list, camera_paths)
    print('images_list_fixed: ', images_list_fixed)
    if (len(images_list_fixed) == 0):
        print('all photos are already exist in chunk.')
        return
    
    start_time = time.perf_counter()
    total_copy_chunk_time = 0
    
    start_import_photo_time = time.perf_counter()
    print('import photos ...')
    chunk.addPhotos(images_list_fixed)
    doc.save()
    end_import_photo_time = time.perf_counter()
    print('import photos time: %f s' % (end_import_photo_time - start_import_photo_time))

    start_import_refernce_time = time.perf_counter()
    # check if ref file txt exist and import
    if ref_path != None and os.path.exists(ref_path):
        print('import reference file ' + ref_path + ' ...')
        chunk.importReference(ref_path, format=Metashape.ReferenceFormatCSV, delimiter=',', columns='nxyzabc', create_markers=False)
        doc.save()
        end_import_refernce_time = time.perf_counter()
        print('import reference time: %f s' % (end_import_refernce_time - start_import_refernce_time))
    
    start_import_mask_time = time.perf_counter()
    if mask_path != None and os.path.exists(mask_path):
        # create a new list append the camera which is new in chunk.cameras not in all_cameras 
        new_cameras = [camera for camera in chunk.cameras if camera not in all_cameras]
        mask_files, mask_name_list = find_files(mask_path, [".jpg", ".jpeg", ".tif", ".tiff"])
        chunk.generateMasks(path=(mask_path + '/{filename}_mask.png'), masking_mode=Metashape.MaskingModeFile, mask_operation=Metashape.MaskOperationReplacement, cameras=new_cameras)
        doc.save()
        end_import_mask_time = time.perf_counter()
        print('import mask time: %f s' % (end_import_mask_time - start_import_mask_time))

    unaligned_cameras = [camera for camera in chunk.cameras if not camera.transform]
    start_match_time = time.perf_counter()
    print('Start matchPhotos...')
    print('num of cameras: ', len(chunk.cameras))
    print('Unaligned cameras: ' + str(len(unaligned_cameras)))
    chunk.matchPhotos(cameras=unaligned_cameras, keypoint_limit = 10000, tiepoint_limit = 4000, keep_keypoints=True, 
            generic_preselection = True, reset_matches=False, 
            filter_stationary_points=False, guided_matching=False)
    doc.save()
    end_match_time = time.perf_counter()
    print('matchPhotos time: %f s' % (end_match_time - start_match_time))

    start_align_time = time.perf_counter()
    print('Start alignCameras...')
    chunk.alignCameras(cameras=unaligned_cameras, adaptive_fitting=True, reset_alignment=False)
    doc.save()
    end_align_time = time.perf_counter()
    print('alignCameras time: %f s' % (end_align_time - start_align_time))

    start_optimizeCamera_time = time.perf_counter()
    chunk.optimizeCameras(adaptive_fitting=True)
    chunk.resetRegion()
    doc.save()
    end_optimizeCamera_time = time.perf_counter()
    print('optimizeCameras time: %f s' % (end_optimizeCamera_time - start_optimizeCamera_time))

    end_time = time.perf_counter()
    
    print('total process time: %f s' % (end_time - start_time))


def print_log(args):
    for i in range(len(args.image_path)):
        print('image path: %s' % args.image_path[i])
    for i in range(len(args.ref_path)):
        print('ref_path: %s' % args.ref_path[i])
    for i in range(len(args.mask_path)):
        print('mask path: %s' % args.mask_path[i])
    for i in range(len(args.split_num)):
        print('split num: %s' % args.split_num[i])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--image_path', '-i', type=str, nargs='*')
    parser.add_argument('--ref_path', '-r', type=str, nargs='*')
    parser.add_argument('--mask_path', '-m', type=str, nargs='*')
    parser.add_argument('--split_num', '-s', type=str, nargs='*')
    parser.add_argument('--output_path', '-o', type=str)
    args = parser.parse_args()

    # test for set of images
    if args.image_path == None or args.output_path == None:
        print("Usage: general_workflow.py <image_folder> <output_folder>")
        raise Exception("Invalid script arguments")
    if args.ref_path != None and len(args.image_path) != len(args.ref_path):
        print_log(args)
        print("Image path, reference path and mask path should have the same length")
        raise Exception("Invalid script arguments")
    if args.mask_path != None and len(args.image_path) != len(args.mask_path):
        print_log(args)
        print("Image path, reference path and mask path should have the same length")
        raise Exception("Invalid script arguments")
    if args.split_num != None and len(args.image_path) != len(args.split_num):
        print_log(args)
        print("Split num and image path must have the same length")
        raise Exception("Invalid script arguments")
    
    mask_path_list = []
    ref_path_list = []
    split_photo_num = []
    if args.ref_path == None:
        ref_path_list = ['' for i in range(len(args.image_path))]
    else:
        ref_path_list = args.ref_path
    if args.mask_path == None:
        mask_path_list = ['' for i in range(len(args.image_path))]
    else:
        mask_path_list = args.mask_path
    if args.split_num == None:
        split_photo_num = [-1 for i in range(len(args.image_path))]
    else:
        split_photo_num = args.split_num
    
    redirect_stdout(args.output_path)
    workflow_incremental_each_photoMask(args.image_path, ref_path_list, mask_path_list, split_photo_num, args.output_path)
    # print("args.ref_path: ", args.ref_path[0])
    # incremental_addPhoto(args.image_path, args.ref_path[0], args.mask_path[0], args.output_path)
    