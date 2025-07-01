import utils
from metashape_utility import MetashapeUtility
import argparse
import os

def set_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_path', '-o', type=str, required=True)
    parser.add_argument('--project_name', '-p', type=str, default='project.psx')
    return parser.parse_args()

def export_ortho(metashape_proj, resolution=0.01):
    export_path = r'D:\GameLab\accident\datas\Xinsheng\part1_0_05'
    # bbox = [303743.928477, 2770023.910637, 303781.156886, 2770099.217802]
    metashape_proj.export_orthomosaic(
        path=export_path,
        resolution=resolution
    )

def export_ortho_folder(metashape_proj):
    export_path = r'D:\GameLab\accident\datas\Xinsheng\temp'
    # ortho 1
    # bbox_list = [
    #     [303743.928477, 2770023.910637, 303781.156886, 2770099.217802],
    #     [303740.417281, 2769884.614712, 303780.115076, 2770006.597494],
    #     [303735.071622, 2769536.623817, 303795.497696, 2769658.229720],
    #     [303818.487241, 2769221.553977, 303896.375320, 2769332.732927],
    #     [303904.666631, 2768969.673981, 303975.770910, 2769071.179735],
    #     [303959.548874, 2768834.014825, 304001.261402, 2768891.443684],
    #     [303960.939307, 2768781.737245, 304003.403361, 2768851.577393]
    # ]
    
    # ortho 2
    bbox_list = [
        [303955.993353, 2768689.101120, 303993.091071, 2768758.085765],
        [303937.950019, 2768506.334585, 303971.392406, 2768575.863641],
        [303924.650837, 2768396.830210, 303959.804230, 2768458.348648],
        [303908.830962, 2768277.188515, 303948.261870, 2768344.851020],
        [303879.354998, 2768120.709252, 303919.719181, 2768192.182633],
        [303856.956375, 2767986.161974, 303893.509682, 2768055.846576],
        [303837.979765, 2767910.955489, 303880.443820, 2767984.295422],
        [303760.620748, 2767696.963152, 303849.877650, 2767791.953056]
    ]
    for i in range(len(bbox_list)):
        index = i + 1
        bbox = bbox_list[i]
        path = os.path.join(export_path, f'ortho_{index}')
        if not os.path.exists(path):
            os.makedirs(path)
        
        metashape_proj.export_orthomosaic(
            path=path,
            name=f'ortho_{index}.tif',
            bbox_min=bbox[:2],
            bbox_max=bbox[2:],
            resolution=0.01
        )

def test_shapely():
    # test shape
    # give coordinates
    # load shape.txt as coordinates. each line is vector 3d
    import numpy as np
    import os
    shape_path = r'D:\GameLab\accident\datas\Xinsheng\shape.txt'
    if not os.path.exists(shape_path):
        print(f"Shape file not found: {shape_path}")
        return
    
    # Read coordinates from file
    with open(shape_path, 'r') as f:
        lines = f.readlines()
        coordinates = [tuple(map(float, line.strip().split())) for line in lines]
    # Make sure the ring is closed
    if coordinates[0] != coordinates[-1]:
        coordinates.append(coordinates[0])

    polygon = Polygon(coordinates)
    from shapely.geometry import Point
    from shapely.geometry import Polygon
    # outside
    outside_point = Point(303889.969514, 2768175.459712)
    # inside
    inside_point = Point(303893.462146, 2768175.210238)

    box_pts = ((303893.462146, 2768175.210238), (303894.462146, 2768175.210238), (303894.462146, 2768174.210238), (303893.462146, 2768174.210238), (303893.462146, 2768175.210238))
    box = Polygon(box_pts)
    print(polygon.contains(outside_point))
    print(polygon.contains(inside_point))
    print(polygon.intersects(box))
    print(polygon.intersection(box))

if __name__ == '__main__':
    args = set_args()

    # print_log(args)

    # redirect metashape logs and separate from standard output

    metashape_proj = MetashapeUtility(args.project_name, args.output_path, "")

    metashape_proj.open_project()

    # metashape_proj.export_camera_transform()
    # metashape_proj.render_top_view(pixel_cm=0.2)
    # export_ortho_folder(metashape_proj)

    export_ortho(metashape_proj, resolution=0.01)
    
            