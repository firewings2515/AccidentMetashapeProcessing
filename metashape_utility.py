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
        self.rolling_shutter_flag = False

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

            mask_files, mask_name_list = find_files(mask_path, [".jpg", ".jpeg", ".tif", ".tiff", ".png"])
            
            mask_camera = [camera for camera in self.new_cameras]
            camera_path = [camera.label for camera in self.new_cameras]

            mask_camera_list = []
            for i in range(0, len(mask_camera)):
                camera = mask_camera[i]
                path = camera_path[i]
                mask_name = pathlib.Path(path).stem + '_mask'
                if (mask_name in mask_name_list):
                    mask_camera_list.append(camera)
            
            if (len(mask_camera_list) == 0):
                print('No mask camera found')
                return

            self.chunk.generateMasks(path=(mask_path + '/{filename}_mask.png'), masking_mode=Metashape.MaskingModeFile, mask_operation=Metashape.MaskOperationReplacement, cameras=mask_camera_list)
            self.doc.save()

            end_import_mask_time = time.perf_counter()
            cost_time = (end_import_mask_time - start_import_mask_time)
            print('import mask time: %f s' % (cost_time))
        
        self.time_list.append(cost_time)

    def match_photos(self):

        if (not self.rolling_shutter_flag):
            self.enable_rolling_shutter_compensation()

        unaligned_cameras = [camera for camera in self.chunk.cameras if not camera.transform]
        start_match_time = time.perf_counter()
        print('Start matchPhotos...')
        print('num of cameras: ', len(self.chunk.cameras))
        print('Unaligned cameras: ' + str(len(unaligned_cameras)))

        self.chunk.matchPhotos(cameras=unaligned_cameras, keypoint_limit = 3000, tiepoint_limit = 4000, keep_keypoints=True, 
                generic_preselection = True, reset_matches=False, 
                reference_preselection=True, reference_preselection_mode=Metashape.ReferencePreselectionSequential,
                filter_stationary_points=False, guided_matching=False,
                filter_mask=True, mask_tiepoints=False)
        self.doc.save()

        end_match_time = time.perf_counter()
        cost_time = (end_match_time - start_match_time)
        print('matchPhotos time: %f s' % (cost_time))
        self.time_list.append(cost_time)

        start_align_time = time.perf_counter()
        print('Start alignCameras...')
        
        self.chunk.alignCameras(cameras=unaligned_cameras, adaptive_fitting=False, reset_alignment=False)
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

        self.chunk.optimizeCameras()
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

        self.chunk.buildPointCloud(replace_asset=True, max_neighbors=10)
        self.doc.save()
        if self.chunk.point_cloud:
            self.chunk.exportPointCloud(os.path.join(self.project_path, self.point_cloud_name), source_data = Metashape.PointCloudData)
            

        end_pointCloud_time = time.perf_counter()
        cost_time = (end_pointCloud_time - start_pointCloud_time)
        print('Build Point cloud time: %f s' % (cost_time))
        self.all_time_list.append([cost_time])

    def build_texture(self, image_list):
        start_texture_time = time.perf_counter()
        print('Start build texture...')

        camera_list = [camera for camera in self.all_cameras if (camera.label in image_list)]
        self.chunk.buildTexture(blending_mode=Metashape.MosaicBlending, texture_size=2048, fill_holes=True, cameras=camera_list)
        self.doc.save()

        end_texture_time = time.perf_counter()
        cost_time = (end_texture_time - start_texture_time)
        print('Build texture time: %f s' % (cost_time))
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

    def enable_rolling_shutter_compensation(self):
        sensors = self.chunk.sensors
        for sensor in sensors:
            sensor.rolling_shutter = Metashape.Shutter.Model.Full
        
        print('enable rolling shutter compensation')

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

    def transform_to_ui_coord(self, coord):
        return self.chunk.crs.project(self.chunk.transform.matrix.mulp(coord))

    def render_top_view(self, mode='model', pixel_cm=0.2):
        # internal coordinates to geographic coordinates: transform_to_ui_coord
        # offset on internal coordinates must be multiplied by region.rot
        
        standard_pixel_cm = 0.2
        # get project parameters
        chunk = self.chunk
        chunk.resetRegion()
        region = chunk.region
        
        real_center = self.transform_to_ui_coord(region.center)
        center = region.center

        # calculate geographic coordinates
        left_x = self.transform_to_ui_coord(center - region.rot*Metashape.Vector([region.size.x * 0.5, 0, 0])).x
        right_x = self.transform_to_ui_coord(center + region.rot*Metashape.Vector([region.size.x * 0.5, 0, 0])).x
        left_z = self.transform_to_ui_coord(center - region.rot*Metashape.Vector([0, 0, region.size.z * 0.5])).z
        right_z = self.transform_to_ui_coord(center + region.rot*Metashape.Vector([0, 0, region.size.z * 0.5])).z
        top_y = self.transform_to_ui_coord(center + region.rot*Metashape.Vector([0, region.size.y * 0.5, 0])).y
        bottom_y = self.transform_to_ui_coord(center - region.rot*Metashape.Vector([0, region.size.y * 0.5, 0])).y
        real_size = Metashape.Vector([abs(right_x - left_x), abs(top_y - bottom_y), abs(right_z - left_z)])
        # print("centerT: ", real_center)
        print("real size:", real_size)

        pixel_m = standard_pixel_cm * 100
        # calculate resolution
        resolution_width = pixel_m * real_size.x
        resolution_height = pixel_m * real_size.z

        # calculate camera render location
        location = region.center
        # print("location: ", location)

        max_resolution = max(resolution_width, resolution_height)
        max_side = max(region.size.x, region.size.z)

        factor = pixel_cm / standard_pixel_cm
        print("factor: ", factor)
        height_factor = 2 * factor
        camera_height = max_side / height_factor
        # location = location + region.rot * Metashape.Vector([0,  camera_height, 0])
        # T = Metashape.Matrix([[1,0,0], [0,0,-1], [0,1,0]])
        print("location: ", location)
        # opposite rotation
        location = location - region.rot * Metashape.Vector([0,  camera_height, 0])
        T = Metashape.Matrix([[1,0,0], [0,0,1], [0,1,0]])
        R = region.rot * T
        cameraT = Metashape.Matrix().Translation(location) * Metashape.Matrix().Rotation(R)    

        calibration = Metashape.Calibration()
        calibration.width = resolution_width * factor
        calibration.height = resolution_height * factor
        print("resolution: ", resolution_width, resolution_height)
        calibration.f = max_resolution // 2
        # print("region size: ", region.size)

        if (mode == 'model'):
            image = self.chunk.model.renderImage(cameraT, calibration)
        elif (mode == 'point_cloud'):
            image = self.chunk.point_cloud.renderImage(cameraT, calibration)
        image.save(os.path.join(self.project_path, f"render_{pixel_cm}.jpg"))

    def export_point_to_pixel(self):
        chunk = self.chunk
        M = chunk.transform.matrix
        crs = chunk.crs
        point_cloud = chunk.tie_points
        projections = point_cloud.projections
        points = point_cloud.points
        npoints = len(points)
        tracks = point_cloud.tracks

        # path = Metashape.app.getSaveFileName("Specify export path and filename:", filter ="Text / CSV (*.txt *.csv);;All files (*.*)")
        path = os.path.join(self.project_path, "point_to_pixel.txt")
        file = open(path, "wt")
        print("Script started...")

        point_ids = [-1] * len(point_cloud.tracks)
        for point_id in range(0, npoints):
            point_ids[points[point_id].track_id] = point_id
        points_proj = {}

        for photo in chunk.cameras:

            if not photo.transform:
                continue
            T = photo.transform.inv()
            calib = photo.sensor.calibration
            
            for proj in projections[photo]:
                track_id = proj.track_id
                point_id = point_ids[track_id]

                if point_id < 0:
                    continue
                if not points[point_id].valid: #skipping invalid points
                    continue

                point_index = point_id
                if point_index in points_proj.keys():
                    x, y = proj.coord
                    points_proj[point_index] = (points_proj[point_index] + "\n" + photo.label + "\t{:.2f}\t{:.2f}".format(x, y))

                else:
                    x, y = proj.coord
                    points_proj[point_index] = ("\n" + photo.label + "\t{:.2f}\t{:.2f}".format(x, y))
            
        for point_index in range(npoints):

            if not points[point_index].valid:
                continue

            coord = M * points[point_index].coord
            coord.size = 3
            if chunk.crs:
                #coord
                X, Y, Z = chunk.crs.project(coord)
            else:
                X, Y, Z = coord

            line = points_proj[point_index]
            
            file.write("{}\t{:.6f}\t{:.6f}\t{:.6f}\t{:s}\n".format(point_index, X, Y, Z, line))

        file.close()					
        print("Finished")
    
    def export_camera_transform(self):
        chunk = self.chunk
        cameras = chunk.cameras

        def wrtie_all_transform(chunk, cameras):

            # path = Metashape.app.getSaveFileName("Specify export path and filename:", filter ="Text / CSV (*.txt *.csv);;All files (*.*)")
            path = os.path.join(self.project_path, "camera_poses.txt")
            file = open(path, "wt")

            print("Script started...")
            # export transform matrix
            for photo in cameras:
                if not photo.transform:
                    continue
                T = photo.transform.inv()
                calib = photo.sensor.calibration
                file.write("{}\t".format(photo.label))
                # save in one line
                translation = photo.transform.translation()

                for j in range(3):
                    for i in range(3):
                        file.write("{:.6f} ".format(T[i, j]))
                        if i == 2:
                            file.write("{:.6f} ".format(translation[j]))
                        if i == 2 and j == 2:
                            # write 0 0 0 1
                            file.write("0.000000 0.000000 0.000000 1.000000")
                            file.write("\n")
            file.close()

            print("Finished")
            
        def wrtie_transform_each_file(chunk, cameras):
            # path = Metashape.app.getSaveFileName("Specify export path and filename:", filter ="Text / CSV (*.txt *.csv);;All files (*.*)")
            path = os.path.join(self.project_path, "cam")
            if (not os.path.exists(path)):
                os.mkdir(path)
            print("Script started...")
            calib = chunk.sensors[0].calibration
            F = calib.f / calib.width
            cx = (calib.width / 2 + calib.cx) / calib.width
            cy = (calib.height / 2 + calib.cy) / calib.height
            # export transform matrix
            for photo in cameras:
                transform_filename = photo.label + ".cam"
                file = open(os.path.join(path, transform_filename), "wt")

                if not photo.transform:
                    continue
                T = photo.transform.inv()
                
                # save in one line
                translation = photo.transform.translation()
                for i in range(len(translation)):
                    file.write("{:.6f} ".format(translation[i]))

                for j in range(3):
                    for i in range(3):
                        file.write("{:.6f} ".format(T[i, j]))

                file.write("\n")
                file.write("{:.6f} {:.6f} {:.6f} {:.6f} {:.6f} {:.6f}\n".format(F, 0, 0, 1, cx, cy))
                file.close()

            print("Finished")
        wrtie_all_transform(chunk, cameras)
    
    def export_orthomosaic(self, path='./', name='ortho_black.tif', resolution=0.01, bbox_min=[0, 0], bbox_max=[0, 0]):
        chunk = self.chunk
        print(chunk.label)
        # path = Metashape.app.getSaveFileName("Specify export path and filename:", filter ="Text / CSV (*.txt *.csv);;All files (*.*)")
        bbox = Metashape.BBox()
        bbox.max = Metashape.Vector(bbox_max)
        bbox.min = Metashape.Vector(bbox_min)
        chunk.exportRaster(
            path=os.path.join(path, name),
            image_format=Metashape.ImageFormatTIFF,
            region=bbox,
            resolution_x=resolution,
            resolution_y=resolution,
            save_alpha=False,
            white_background=False
        )
