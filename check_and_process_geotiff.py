#!/usr/bin/env python3
# -*- coding: utf-8 -*-
## Meta Data ##

#  Script: Check and Process GeoTiff                                                                    
#  Developed By: Faizan Tayyab                                                                  
#  Date: 02/11/2020                                                                   
#  Project: COGs generation     
# #########################################################################                                                             
#  Copyright (c) 2020, Faizan Tayyab
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.

# Import the validation script

from validate_cloud_optimized_geotiff import validate
import glob
from osgeo import gdal
import os
import shutil

def process_raster(source_ras,dest_dir):
    """ 
        Function used to process the raster
        Params: source raster, Destination Directory
        Returns: Output Folder
    """
    destination_ras = os.path.join(dest_dir,os.path.basename(source_ras))
    
    # https://gdal.org/drivers/raster/gtiff.html (check creation options)
    # PREDICTOR works with compression and helps to reduce file sizes especially if there are not abrupt changes to the pixel values
    
    ds = gdal.Translate(destination_ras,source_ras, options = "-co TILED=YES -co BLOCKXSIZE=512 -co BLOCKYSIZE=512 -co COPY_SRC_OVERVIEWS=YES -co COMPRESS=LZW -co PREDICTOR=2 -co BIGTIFF=YES")
    
    if ds is None:
        print('Failed to Process: ' + source_ras)
    else:
        # Validating the GeoTIFFs after conversion to COGs
        validation_result = validate(ds, full_check=True)
        if len(validation_result[2]) == 0:
            print(str(destination_ras) + ' is valid COG')
            final_ras = os.path.join(os.path.join(dest_dir,'3857'),os.path.basename(source_ras))
            
            # https://gdal.org/programs/gdalwarp.html (check for all options)
            # Use Warp to transform (re-project the GeoTiffs)
            gdal.Warp(final_ras,destination_ras,dstSRS='EPSG:3857',format="GTiff",warpMemoryLimit=3000,outputType=gdal.GDT_Float32,resampleAlg="cubicspline",creationOptions=["TILED=YES","COMPRESS=DEFLATE","NUM_THREADS=ALL_CPUS","BIGTIFF=YES","COPY_SRC_OVERVIEWS=YES"])
   
    return os.path.join(destination_ras,'3857')
    
def main():
    # get current working directory
    current_dir = os.getcwd()

    # Set the source directory
    source_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'source')
    
    # Change directory
    os.chdir(source_dir)
    
    # Get all tiff files only
    tf_files = glob.glob(os.path.join(source_dir,'*.TIF'))
    
    if len(tf_files)>0:
        # Check all Files for validation
        validation_results = [validate(tiff, full_check=True) for tiff in tf_files]
        
        #print(validation_results)
        to_be_processed = []
        for filename,warnings,errors,details in validation_results:
            if warnings:
                print('The following warnings were found:')
                for warning in warnings:
                    print(' - ' + warning)
                print('')

            if errors:
                print('%s is NOT a valid cloud optimized GeoTIFF.' % filename)
                to_be_processed.append(filename)
                print('The following errors were found:')
                for error in errors:
                    print(' - ' + error)
                print('')
            else:
                print('%s is a valid cloud optimized GeoTIFF' % filename)
        
            if not warnings and not errors:
                headers_size = min(details['data_offsets'][k] for k in details['data_offsets'])
                if headers_size == 0:
                    headers_size = gdal.VSIStatL(filename).size
                    print('\nThe size of all IFD headers is %d bytes' % headers_size)
        
        # Check if any file needs to be processed
        if len(to_be_processed) > 0:
            translated_path = os.path.join(source_dir,'translated')
            if os.path.isdir(translated_path):
                shutil.rmtree(translated_path)  
            try:
                os.mkdir(translated_path)
                os.mkdir(os.path.join(translated_path,'3857'))
            except OSError:
                print ("Creation of the directory %s failed or it already exists" % os.path.join(source_dir,'translated'))
            else:
                print ("Successfully created the directory %s " % os.path.join(source_dir,'translated'))
            
            output_path = [process_raster(tiff,translated_path) for tiff in to_be_processed]
            
            #os.chdir(output_path[0])
            # Build VRT file https://gdal.org/programs/gdalbuildvrt.html
            #os.system('gdalbuildvrt eu_dem_v11.vrt *.TIF')
            
            print('All Geotiffs have been processed')
        else:
            print('No Processing Required')
        os.chdir(current_dir)
    
if __name__ == '__main__':
    main()