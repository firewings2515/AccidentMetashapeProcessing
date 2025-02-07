import Metashape
import os, time
import sys
# use for split filename and extension
import pathlib
import csv
from utils import find_files
import math

class MetashapeUtility:
    def __init__(self, project_name, output_path, pc_name):

        self.check_compatibility()
        self.project_name = project_name
        self.project_path = output_path

        self.doc = Metashape.Document()

        self.copy_flag = False

        self.all_cameras = []
        self.new_cameras = []

        self.check_gpu_device()

        # time list until photo match
        self.start_time = time.perf_counter()
        self.time_list = []
        self.all_time_list = []

        self.point_cloud_name = pc_name

    def check_compatibility(self):
        # Checking compatibility
        compatible_major_version = "2.1"
        found_major_version = ".".join(Metashape.app.version.split('.')[:2])
        if found_major_version != compatible_major_version:
            raise Exception("Incompatible Metashape version: {} != {}".format(found_major_version, compatible_major_version))
    
    def check_gpu_device(self):
        # set all gpu on. disable cpu if there is any gpu
        Metashape.app.gpu_mask = 2**len(Metashape.app.enumGPUDevices()) - 1
        if Metashape.app.gpu_mask:
            Metashape.app.cpu_enable = False 
        else:
            Metashape.app.cpu_enable = True
    
    def open_project(self):
        # set project
        project_full_path = os.path.join(self.project_path, self.project_name)
        if os.path.isfile(project_full_path):
            self.doc.open(project_full_path)
        else:
            self.doc.save(project_full_path)
        
        # set chunk to first chunk
        if (len(self.doc.chunks) == 0):
            self.chunk = self.doc.addChunk()
        else:
            self.chunk = self.doc.chunks[0]
        self.doc.read_only = False
        self.all_cameras = self.chunk.cameras

    def add_photos(self, photos):

        camera_paths = [camera.label for camera in self.all_cameras]

        new_images_list = [item for item in photos if pathlib.Path(item).stem not in camera_paths]

        if (len(new_images_list) == 0):
            return False
        print('new_images_number: ', len(new_images_list))

        start_import_photo_time = time.perf_counter()
        print('import photos ...')
        self.time_list.insert(0, len(new_images_list))

        self.chunk.addPhotos(new_images_list)
        self.doc.save()
        self.new_cameras = [camera for camera in self.chunk.cameras if camera not in self.all_cameras]

        end_import_photo_time = time.perf_counter()
        cost_time = (end_import_photo_time - start_import_photo_time)
        print('import photos time: %f s' % (cost_time))
        self.time_list.append(cost_time)

        return True

    def import_reference(self, ref_path):
        cost_time = 0

        start_import_refernce_time = time.perf_counter()
        if os.path.exists(ref_path):
            print('import reference file ' + ref_path + ' ...')
            
            self.chunk.importReference(ref_path, format=Metashape.ReferenceFormatCSV, delimiter=',', columns='nxyzabc', create_markers=False)
            self.doc.save()

            end_import_refernce_time = time.perf_counter()
            cost_time = (end_import_refernce_time - start_import_refernce_time) 
            print('import reference time: %f s' % (cost_time))
            
        
        self.time_list.append(cost_time)

    def import_mask(self, mask_path):
        cost_time = 0

        start_import_mask_time = time.perf_counter()
        if os.path.exists(mask_path):
            print('import mask file ' + mask_path + ' ...')
            mask_files, mask_name_list = find_files(mask_path, [".jpg", ".jpeg", ".tif", ".tiff"])
            
            self.chunk.generateMasks(path=(mask_path + '/{filename}_mask.png'), masking_mode=Metashape.MaskingModeFile, mask_operation=Metashape.MaskOperationReplacement, cameras=self.new_cameras)
            self.doc.save()

            end_import_mask_time = time.perf_counter()
            cost_time = (end_import_mask_time - start_import_mask_time)
            print('import mask time: %f s' % (cost_time))
        
        self.time_list.append(cost_time)

    def match_photos(self):
        unaligned_cameras = [camera for camera in self.chunk.cameras if not camera.transform]
        start_match_time = time.perf_counter()
        print('Start matchPhotos...')
        print('num of cameras: ', len(self.chunk.cameras))
        print('Unaligned cameras: ' + str(len(unaligned_cameras)))

        self.chunk.matchPhotos(cameras=unaligned_cameras, keypoint_limit = 3000, tiepoint_limit = 4000, keep_keypoints=True, 
                generic_preselection = True, reset_matches=False, 
                filter_stationary_points=False, guided_matching=False)
        self.doc.save()

        end_match_time = time.perf_counter()
        cost_time = (end_match_time - start_match_time)
        print('matchPhotos time: %f s' % (cost_time))
        self.time_list.append(cost_time)

        start_align_time = time.perf_counter()
        print('Start alignCameras...')
        
        self.chunk.alignCameras(cameras=unaligned_cameras, adaptive_fitting=True, reset_alignment=False)
        self.doc.save()
        end_align_time = time.perf_counter()
        cost_time = (end_align_time - start_align_time)
        
        print('alignCameras time: %f s' % (cost_time))
        self.time_list.append(cost_time)
        
        # update camera and time list after each round of matching
        self.all_cameras = self.chunk.cameras
        self.all_time_list.append(self.time_list)
        self.time_list = []
    
    def optimize_cameras(self):
        start_optimizeCamera_time = time.perf_counter()
        print('Start optimize camera...')

        self.chunk.optimizeCameras(adaptive_fitting=True)
        self.chunk.resetRegion()
        self.doc.save()

        end_optimizeCamera_time = time.perf_counter()
        cost_time = (end_optimizeCamera_time - start_optimizeCamera_time)
        print('optimizeCameras time: %f s' % (cost_time))
        self.all_time_list.append([cost_time])

    def build_depthMaps(self):
        start_depthMap_time = time.perf_counter()
        print('Start build depth maps...')
        
        self.chunk.buildDepthMaps(downscale = 4, filter_mode = Metashape.MildFiltering)
        self.doc.save()

        end_depthMap_time = time.perf_counter()
        cost_time = (end_depthMap_time - start_depthMap_time)
        print('buildDepthMaps time: %f s' % (cost_time))
        self.all_time_list.append([cost_time])

    def build_pointCloud(self):
        start_pointCloud_time = time.perf_counter()
        print('Start build point cloud...')

        self.chunk.buildPointCloud(replace_asset=True)
        self.doc.save()
        if self.chunk.point_cloud:
            self.chunk.exportPointCloud(os.path.join(self.project_path, self.point_cloud_name), source_data = Metashape.PointCloudData)
            

        end_pointCloud_time = time.perf_counter()
        cost_time = (end_pointCloud_time - start_pointCloud_time)
        print('Build Point cloud time: %f s' % (cost_time))
        self.all_time_list.append([cost_time])

    def copy_chunk(self):
        copy_chunk = self.chunk.copy(keypoints=True, items=[Metashape.DataSource.PointCloudData, Metashape.DataSource.DepthMapsData])
        copy_chunk.label = 'copy' + str(len(self.doc.chunks) - 1)
        self.doc.save()

    def end_time_list(self):
        end_time = time.perf_counter()
        cost_time = (end_time - self.start_time)
        print('total process time: %f s' % (cost_time))
        self.all_time_list.append([cost_time])

    def save_camera_error(self, error_name):
        error_list = []
        for camera in self.all_cameras:
            if (camera.transform):
                camera_error = self.cal_camera_error(camera)
                error_list.append([camera.label, camera_error])
        
        filename = os.path.join(self.project_path, error_name)
        # output txt
        with open(filename, 'w', encoding='utf-8') as f:
            write = csv.writer(f)
            write.writerows(error_list)


    def cal_camera_error(self, camera):
        # reference from https://github.com/agisoft-llc/metashape-scripts/blob/master/src/save_estimated_reference.py#L94
        chunk = self.chunk

        estimated_location = None
        estimated_rotation = None
        reference_location = None
        reference_rotation = None
        error_location = None
        error_rotation = None
        distance_location = None

        transform = chunk.transform.matrix
        crs = chunk.crs

        if chunk.camera_crs:
            transform = Metashape.CoordinateSystem.datumTransform(crs, chunk.camera_crs) * transform
            crs = chunk.camera_crs
        
        ecef_crs = Metashape.CoordinateSystem('LOCAL')

        camera_transform = transform * camera.transform
        antenna_transform = self.getAntennaTransform(camera.sensor)
        location_ecef = camera_transform.translation() + camera_transform.rotation() * antenna_transform.translation()
        rotation_ecef = camera_transform.rotation() * antenna_transform.rotation()

        estimated_location = Metashape.CoordinateSystem.transform(location_ecef, ecef_crs, crs)
        if camera.reference.location:
            reference_location = camera.reference.location
            distance_location = math.dist(reference_location, estimated_location)
            error_location = Metashape.CoordinateSystem.transform(estimated_location, crs, ecef_crs) - Metashape.CoordinateSystem.transform(reference_location, crs, ecef_crs)
            error_location = crs.localframe(location_ecef).rotation() * error_location

        if chunk.euler_angles == Metashape.EulerAnglesOPK or chunk.euler_angles == Metashape.EulerAnglesPOK:
            localframe = crs.localframe(location_ecef)
        else:
            localframe = ecef_crs.localframe(location_ecef)

        estimated_rotation = Metashape.utils.mat2euler(localframe.rotation() * rotation_ecef, chunk.euler_angles)
        if camera.reference.rotation:
            reference_rotation = camera.reference.rotation
            error_rotation = estimated_rotation - reference_rotation
            error_rotation.x = (error_rotation.x + 180) % 360 - 180
            error_rotation.y = (error_rotation.y + 180) % 360 - 180
            error_rotation.z = (error_rotation.z + 180) % 360 - 180
        
        return distance_location

    def getAntennaTransform(self, sensor):
        location = sensor.antenna.location
        if location is None:
            location = sensor.antenna.location_ref
        if location is None:
            location = Metashape.Vector([0.0, 0.0, 0.0])
        rotation = sensor.antenna.rotation
        if rotation is None:
            rotation = sensor.antenna.rotation_ref
        if rotation is None:
            rotation = Metashape.Vector([0.0, 0.0, 0.0])
        return Metashape.Matrix.Diag((1, -1, -1, 1)) * Metashape.Matrix.Translation(location) * Metashape.Matrix.Rotation(Metashape.Utils.ypr2mat(rotation))

    def save_unalign_log(self, unalign_name):
        # unaligned_cameras = [camera.label for camera in self.chunk.cameras if not camera.transform]
        camera_alignments = []
        for camera in self.chunk.cameras:
            camera_status = []
            camera_id = camera.label.split('_')[-1]
            camera_status.append(camera_id)
            if not camera.transform:
                camera_status.append("false")
            else:
                camera_status.append("true")
            camera_alignments.append(camera_status)
        filename = os.path.join(self.project_path, unalign_name)
        # output txt
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            write = csv.writer(f)
            write.writerows(camera_alignments)

    def save_log(self):
        count = 0
        while True:
            filename = os.path.join(self.project_path, f'result{count}.csv')
            if not os.path.isfile(filename):
                break
            count += 1

        # output csv
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            write = csv.writer(f)
            write.writerows(self.all_time_list)