import fast
import matplotlib.pyplot as plt
import numpy as np
import cv2 as cv
import os
from tqdm import tqdm
import argparse
import json


parser = argparse.ArgumentParser(description='Extract patches from WSI and segmentation masks')
parser.add_argument('-w', '--wsi_path', help="path to wsi file", type=str)
parser.add_argument('-n', '--nuclei_tiff_path',help = 'generate this file with nuclei-segmentation.py', type=str)
parser.add_argument('-e', '--epithelium_tiff_path',help = 'generate this file with colon-epithelium-segmentation-with-postprocessing.py', type=str)
parser.add_argument('-o', '--output_dir', type = str, default = None)
parser.add_argument('-v', '--patch_visualization', help = 'save a visualization with image patches and mask.\\ Warning : This could take some time', action ="store_true", default = False)
parser.add_argument('-b', '--bgremoved', help = 'If true skips bground patches', action="store_true")

def get_access_to_tiff(tiff_path : str, level : int) -> tuple:

    # Run importer and get data from mask
    mask_pyramid_image = fast.fast.TIFFImagePyramidImporter\
        .create(tiff_path)\
        .runAndGetOutputData()

    w = mask_pyramid_image.getLevelWidth(level)
    h = mask_pyramid_image.getLevelHeight(level)

    # Extract specific patch at highest resolution
    access_mask = mask_pyramid_image.getAccess(fast.ACCESS_READ)
    
    return access_mask, w, h

def get_mask_from_access(access: tuple, x : int, y : int, W: int, H:int, patch_size : int)-> np.ndarray:
    
    w = access[1]
    h = access[2]

    x = int(x/W*w)
    y = int(y/H*h)
    mask = np.asarray(access[0].getPatchAsImage(config['level'], x, y, int(patch_size/W*w), int(patch_size/H*h)))
    mask = (mask*255).astype(np.uint8)
    mask = cv.resize(mask,(patch_size,patch_size))

    return mask 

def extract_all_patches(WSI_path : str, TIFF_path_1 : str, TIFF_path_2 : str, config : dict):
    
    # Run importer and get data
    wsi_pyramid_image = fast.fast.TIFFImagePyramidImporter\
        .create(WSI_path)\
        .runAndGetOutputData()

    W = wsi_pyramid_image.getLevelWidth(config['level'])
    H = wsi_pyramid_image.getLevelHeight(config['level'])

    config['wsi_width'] = W
    config['wsi_height'] = H

    access_wsi_image = wsi_pyramid_image.getAccess(fast.ACCESS_READ)

    access_1 = get_access_to_tiff(tiff_path= TIFF_path_1, level= config['level'])
    access_2 = get_access_to_tiff(tiff_path= TIFF_path_2, level= config['level'])

    for y in tqdm(range(0,H-config['patch_size'],config['patch_size'])):
        for x in range(0,W-config['patch_size'],config['patch_size']):

            wsi_image = np.asarray(access_wsi_image.getPatchAsImage(config['level'], x, y, config['patch_size'],config['patch_size']))

            if(config['bgremoved']):
                gpatchmean = cv.cvtColor(wsi_image, cv.COLOR_BGR2GRAY).mean()
                if(gpatchmean>200 or gpatchmean<50):
                    continue

            mask = np.zeros((config['patch_size'],config['patch_size'],3))
            mask[:,:,config['channel_nuclei']] = get_mask_from_access(access_1, x, y, W, H, config['patch_size'])
            mask[:,:,config['channel_epithelium']] = get_mask_from_access(access_2, x, y, W, H, config['patch_size'])

            cv.imwrite(os.path.join(config['output_dir'],'masks',f"{config['output_dir']}_{config['level']}_{y}_{x}.png"),mask)
            cv.imwrite(os.path.join(config['output_dir'],'patches',f"{config['output_dir']}_{config['level']}_{y}_{x}.png"),wsi_image[:,:,::-1])

            if config['patch_visualization']:
                plt.figure(figsize = (8,8))
                plt.imshow(wsi_image)
                plt.imshow(mask,alpha = 0.3,cmap = 'gray')
                level = config['level']
                plt.savefig(os.path.join(config['output_dir'],f'image_{level}_{y}_{x}.png'))
                plt.show()

    
    with open(os.path.join(output_dir,'report.json'), "w") as file:
        json.dump(config, file)
    return 

if __name__ == "__main__":

    args = parser.parse_args()

    if args.output_dir is None :
        output_dir = os.path.basename(args.wsi_path).split('.')[0]
    else :
        output_dir = args.output_dir

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
        os.mkdir(os.path.join(output_dir,'patches'))
        os.mkdir(os.path.join(output_dir,'masks'))

    # Load the configuration from the JSON file
    with open('src/config.json', 'r') as config_file:
        params = json.load(config_file)

    # Create a dictionary to hold the imported parameters
    config = {}

    config['bgremoved'] = args.bgremoved
    config['patch_visualization'] = args.patch_visualization
    config['output_dir'] = output_dir

    parameter_names = ['level','patch_size','channel_nuclei','channel_epithelium', 'patch_size_preprocessing']
    
    for param_name in parameter_names:
        if param_name in params:
            config[param_name] = params[param_name]

    extract_all_patches(args.wsi_path, args.nuclei_tiff_path, args.epithelium_tiff_path , config)





