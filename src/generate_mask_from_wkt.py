#!/usr/bin/env python3
"""Generate binary mask from wkt polygons

# cd ~/results/graffiti/20200101-deeplab/20191221-gsvcities_wkt/wkt/ && for D in *; do python ~/projects/graffiti-deeplab/src/generate_mask_from_wkt.py  --wktdir ~/results/graffiti/20200101-deeplab/20191221-gsvcities_wkt/wkt/$D --outdir /tmp/mask/$D ; done
"""

import os
import argparse
import logging
from os.path import join as pjoin
from logging import debug, info
import numpy as np
import cv2
import shapely.wkt
from shapely.geometry import Polygon

##########################################################
def draw_edge_mask_from_wkt(polys, maskpath, imgorig=[]):
    backgrcolor = 0
    foregrcolor = [256, 256, 256, 0.5]

    if len(imgorig) == 0:
        img = np.ones((640, 640), dtype=np.uint8) * backgrcolor

    img = cv2.Canny(imgorig, 100, 200)
    stencil = np.zeros(img.shape).astype(img.dtype)
    cv2.fillPoly(stencil, polys, foregrcolor, lineType=8, shift=0)
    img = cv2.bitwise_and(img, stencil)
    cv2.imwrite(maskpath, img)

##########################################################
def parse_wkt(wktpath):
    wktfh = open(wktpath)
    f = shapely.wkt.loads(wktfh.read())

    polys = []
    for poly in f:
        coords = []
        for x, y in zip(*poly.exterior.coords.xy):
            coords.append([int(x), int(y)])
        polys.append(np.array(coords))

    wktfh.close()
    return np.array(polys)

def draw_mask_from_wkt(polys, maskpath, imgorig=[]):
    backgrcolor = 0
    foregrcolor = [256, 256, 256, 0.5]

    if len(imgorig) == 0:
        img = np.ones((640, 640), dtype=np.uint8) * backgrcolor

    img = imgorig.copy()
    stencil = np.zeros(img.shape).astype(img.dtype)
    cv2.fillPoly(stencil, polys, foregrcolor, lineType=8, shift=0)
    img = cv2.bitwise_and(img, stencil)
    cv2.imwrite(maskpath, img)

##########################################################
def draw_polygon_from_wkt(polys, maskpath, imgorig=[]):
    edgecolor = (0, 0, 255)
    if len(imgorig) == 0:
        img = np.ones((640, 640), dtype=np.uint8) * backgrcolor

    img = imgorig.copy()

    for p in polys:
        cv2.polylines(img, np.int32([p]), 1, edgecolor, thickness=3)

    cv2.imwrite(maskpath, img)

def filter_polys_by_area(polys, minarea):
    todel = []
    for i, poly in enumerate(polys):
        polyarea = Polygon(poly).area
        if polyarea < minarea:
            todel.append(i)

    x = np.delete(polys, todel, axis=0)
    return x

##########################################################
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wktdir', required=True,
                        help='Path to the polygons in wkt format')
    parser.add_argument('--outdir', default='/tmp', help='Output directory')
    args = parser.parse_args()

    logging.basicConfig(format='[%(asctime)s] %(message)s',
    datefmt='%Y%m%d %H:%M', level=logging.DEBUG)

    imgsdir = '/media/frodo/6TB_A/gsvcities/20180511-gsv_spcity/img'
    if not os.path.exists(args.outdir): os.mkdir(args.outdir)

    np.random.seed(0)
    samplesz = 2000
    minarea = 4900

    acc = 0

    files = sorted(os.listdir(args.wktdir))
    np.random.shuffle(files)

    fh = open('/tmp/analyzedimgs.txt', 'w')
    for i, f in enumerate(files):
        if acc == samplesz: break
        if not f.endswith('.wkt'): continue
        wktpath = pjoin(args.wktdir, f)
        if os.stat(wktpath).st_size == 0: continue
        print(wktpath)

        maskpath = pjoin(args.outdir, f.replace('.wkt', '_mask.jpg'))
        edgespath = pjoin(args.outdir, f.replace('.wkt', '_edges.jpg'))
        polypath = pjoin(args.outdir, f.replace('.wkt', '_poly.jpg'))
        img = cv2.imread(pjoin(imgsdir, f.replace('.wkt', '.jpg')))

        polys = parse_wkt(wktpath)
        polys = filter_polys_by_area(polys, minarea)
        if len(polys) == 0: continue
        # draw_mask_from_wkt(polys, maskpath, img)
        # draw_edge_mask_from_wkt(polys, edgespath, img)
        # print(img)
        draw_polygon_from_wkt(polys, polypath, img)
        fh.write(f.replace('.wkt', '') + '\n')
        acc += 1
    fh.close()
    print(acc)

if __name__ == "__main__":
    main()

