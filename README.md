## `metashape_run` Usage Guidelines

- `python metashape_run.py -r <data_path>`  
- `-r` : (Required) Absolute data path which contains capture image folder and arpose text file  
- `-p` : metashape project generatation path. Default: Equal to the data root path.  
- `--usage` : The align mode is used by default if not provided by user.  
    - usage list : [`align`, `pointCloud`]  
    - `align` : match photo alignment. generate tie points.  
    - `pointCloud` : build point cloud from first chunk.  
---
- example: run alignment and generate metashape project under data_path  
    - `python metashape_run.py -r "F:\accidentProj\20241118_023406_680\metashape"`  
- example: run alignment and generate metashape project under given project path  
    - `python metashape_run.py -r "F:\accidentProj\20241118_023406_680\metashape" -p "F:\accidentProj\metashape\test"`  
- example: build point cloud in given project path  
    - `python metashape_run.py -r "F:\accidentProj\20241118_023406_680\metashape" -p "F:\accidentProj\metashape\test" --usage pointCloud`  