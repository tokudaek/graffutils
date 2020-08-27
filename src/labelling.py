#!/usr/bin/env python3
"""Analyze labels generated by mannual classification of the crops
"""

import argparse
import time
from os.path import join as pjoin
import os
import inspect

import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
import matplotlib.collections as mc
import matplotlib.patches as mpatches
import pandas as pd
from scipy.spatial import cKDTree
import scipy.stats as stats
import igraph
import geopandas as geopd
import matplotlib_venn
from src.utils import info, export_individual_axis, hex2rgb
# plt.style.use('seaborn')
from myutils import graph

palettehex = ['#8dd3c7','#bebada','#fb8072','#80b1d3','#fdb462','#b3de69']
palette = hex2rgb(palettehex, normalized=True, alpha=1.0)
palettehex2 = ['#1b9e77','#d95f02','#7570b3','#e7298a']
palette2 = hex2rgb(palettehex2, normalized=True, alpha=1.0)
palettehex3 = ['#e41a1c','#377eb8','#e6e600','#984ea3','#ff7f00','#4daf4a','#a65628','#f781bf','#999999']
palette3 = hex2rgb(palettehex3, normalized=True, alpha=.7)
palette3[5,3] = 1.0

##########################################################
def plot_types(infomapout, shppath, clulabelspath, outdir):
    np.random.seed(0)
    df = pd.read_csv(clulabelspath, index_col='id')
    totalrows = len(df)

    fig, ax = plt.subplots(1, 1, figsize=(15/2, 10), squeeze=False) # Plot contour
    geodf = geopd.read_file(shppath)
    shapefile = geodf.geometry.values[0]
    
    xs, ys = shapefile.exterior.xy
    ax[0, 0].plot(xs, ys, c='dimgray')

    clusters = np.unique(df.cluster)
    clusters_str = ['C{}'.format(cl) for cl in clusters]
    nclusters = len(clusters)
    labels = np.unique(df.label)
    nlabels = len(labels)

    markers = ['$A$', '$B$', '$C$']
    ss = [30, 35, 35]
    edgecolours = ['#993333', '#339933', '#3366ff']
    visual = [ dict(marker=m, s=s, edgecolors=e) for m,s,e in \
              zip(['o', 'o', 'o'], ss, edgecolours)]

    for i, l in enumerate(labels):
        data = df[df.label == l]
        ax[0, 0].scatter(data.x, data.y, c=edgecolours[i],
                         label='Type ' + markers[i],
                         alpha=0.6,
                         # linewidths=0.2,
                         # edgecolor=(0.3, 0.3, 0.3, 1),
                         **(visual[i]))
    
    fig.patch.set_visible(False)
    ax[0, 0].axis('off')

    ax[0, 0].legend(loc=(0.6, 0.12), title='Graffiti types',
                    fontsize='xx-large', title_fontsize='xx-large')

    extent = ax[0, 0].get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(pjoin(outdir, 'map_types.pdf'), bbox_inches=extent.expanded(1.0, 1.0))

##########################################################
def plot_counts_normalized(clulabelspath, cluareaspath, outdir):
    df = pd.read_csv(clulabelspath, index_col='id')
    totalrows = len(df)

    clusters = np.unique(df.cluster)
    clusters_str = ['C{}'.format(cl) for cl in clusters]
    nclusters = len(clusters)
    labels = np.unique(df.label)
    nlabels = len(labels)
    # labels_str = [str(l) for l in labels]
    plotsize = 5
    alpha = 0.6
    palette = np.array([
        [27.0,158,119],
        [217,95,2],
        [117,112,179],
        [231,41,138],
        [102,166,30],
        [230,171,2],
    ])
    palette /= 255.0
    colours = np.zeros((palette.shape[0], 4), dtype=float)
    colours[:, :3] = palette
    colours[:, -1] = alpha

    counts = np.zeros(nclusters, dtype=int)
    countsnorm = np.zeros(nclusters)
    areas = pd.read_csv(cluareaspath)

    for i, cl in enumerate(clusters):
        data = df[df.cluster == cl]
        counts[i] = len(data)
        points = data[['x', 'y']].values

        countsnorm[i] = counts[i] / areas.iloc[i]

    fig, ax = plt.subplots(1, 1, figsize=(2*plotsize, plotsize),
                           squeeze=False)
    yfactor = 1
    ax[0, 0].bar(clusters_str, countsnorm / yfactor, color=colours)
    ax[0, 0].set_ylabel('Normalized count of graffitis')
    ax[0, 0].set_xlabel('Community')
    i = 0
    for spine in ax[0, i].spines.values():
        spine.set_edgecolor('dimgray')
    ax[0, i].ticklabel_format(axis="y", style="sci", scilimits=(0,0))
    ax[0, i].spines['top'].set_visible(False)
    ax[0, i].spines['right'].set_visible(False)
    ax[0, i].yaxis.grid(True, alpha=0.4)
    ax[0, i].set_axisbelow(True)
    # ax[0, i].spines['left'].set_visible(False)

    plt.savefig(pjoin(outdir, 'countsnormalized.pdf'))

##########################################################
def count_labels_per_region(df, clusters, labels, cluids):
    """Count number of labels per region """
    nlabels = len(labels)
    nclusters = len(clusters)

    counts = np.ones((nclusters, nlabels), dtype=float)
    for i in range(nclusters):
        labels_reg, counts_reg = np.unique(df[df.index.isin(cluids[i])].label,
                                           return_counts=True)
        for j in range(nlabels):
            lab = labels[j]
            if not lab in labels_reg: continue
            ind = np.where(labels_reg == lab)
            counts[i, j] = counts_reg[ind]
    return counts

#############################################################
def shuffle_labels(labelspath, outdir):
    """Shuffle labels from @labelspath and compute metrics """
    info(inspect.stack()[0][3] + '()')
    df = pd.read_csv(labelspath, index_col='id')

    nrealizations = 10
    labels = np.unique(df.label)
    clusters = np.unique(df.cluster)
    nlabels = len(labels)
    nclusters = len(clusters)
    info('nrealizations:{}, nclusters:{}'.format(nrealizations, nclusters))

    cluids = {}
    for i in range(nclusters):
        # cluids[i] = df[df.cluster == clusters[i]].index
        cluids[i] = np.where(df.cluster.values == clusters[i])[0]

    counts_orig = count_labels_per_region(df, clusters, labels, cluids)
    counts_perm = count_shuffled_labels_per_region(df, clusters, labels,
            cluids, nrealizations)

    plot_shuffle_distrib_and_orig(counts_orig, counts_perm, nclusters,
            nlabels, outdir)

##########################################################
def compile_lists(listsdir, labelspath):
    """Compile lists (.lst) in @listdir """
    info(inspect.stack()[0][3] + '()')
    files = sorted(os.listdir(listsdir))

    cols = 'img,x,y,label'.split(',')
    data = []
    for f in files:
        if not f.endswith('.lst'): continue
        label = int(f.replace('.lst', '').split('_')[1])
        lines = open(pjoin(listsdir, f)).read().strip().splitlines()
        for l in lines:
            id = l.replace('.jpg', '')
            _, y, x, heading = id.split('_')
            data.append([l, x, y, label])
    
    df = pd.DataFrame(data, columns=cols)
    df.to_csv(labelspath, index_label='id',)

#############################################################
def compile_labels(annotdir, labelspath):
    """Summarize @annotdir csv annotations in .txt format and output
    summary to @labelspath """
    info(inspect.stack()[0][3] + '()')

    if os.path.exists(labelspath):
        info('Loading {}'.format(labelspath))
        return pd.read_csv(labelspath)

    files = sorted(os.listdir(annotdir))

    labels = '1 2 3'.split(' ')
    info('Using labels:{}'.format(labels))

    cols = 'img,x,y,label'.split(',')
    data = []
    for f in files:
        if not f.endswith('.txt'): continue
        filepath = pjoin(annotdir, f)
        _, y, x, heading = os.path.split(filepath)[-1].replace('.txt', '').split('_')
        labels_ = open(filepath).read().strip().split(',')

        for l in labels_: # each label in the file correspond to a new row
            img = f.replace('.txt', '.jpg')
            data.append([img, x, y, l])

    df = pd.DataFrame(data, columns=cols)
    df.to_csv(labelspath, index_label='id',)
    return df

##########################################################
def parse_infomap_results(graphml, infomapout, labelsdf, annotator, outpath):
    """Find enclosing community given by @infomapout of each node in @graphml """
    info(inspect.stack()[0][3] + '()')

    if os.path.exists(outpath):
        return pd.read_csv(outpath)

    g = graph.simplify_graphml(graphml, directed=True, simplify=True)
    cludf = pd.read_csv(infomapout, sep=' ', skiprows=[0, 1],
                     names=['id', 'cluster','flow']) # load graph clusters
    cludf = cludf.sort_values(by=['id'], inplace=False)

    coords_objs = np.zeros((len(labelsdf), 2))
    
    i = 0
    for _, row in labelsdf.iterrows():
        coords_objs[i, 0] = row.x
        coords_objs[i, 1] = row.y
        i += 1

    coords_nodes = np.array([g.vs['x'], g.vs['y']]).T

    kdtree = cKDTree(coords_nodes)
    dists, inds = kdtree.query(coords_objs)
    labelsdf['cluster'] = np.array(cludf.cluster.tolist())[inds]
    # labelsdf['annotator'] = annotator
    labelsdf.to_csv(outpath, index=False, float_format='%.08f')
    return labelsdf

##########################################################
def convert_csv_to_annotdir(labelsclu, annotator, outdir):
    """Convert dataframe in @labelsclu from @annotator to txt format in @outdir """
    info(inspect.stack()[0][3] + '()')
    df = pd.read_csv(labelsclu)
    labels = np.unique(df.label)
    labeldir = pjoin(outdir, 'annot')
    if not os.path.isdir(labeldir): os.mkdir(labeldir)

    filtered = df[(df.annotator == annotator)]
    imgs = np.unique(filtered.img)

    for im in imgs:
        aux = filtered[filtered.img == im]
        mylabels = sorted(np.array(list(set(aux.label))).astype(str))
        if '1' in mylabels and len(mylabels) == 1: print(im)
        mylabelsstr = ','.join(mylabels)
        annotpath = pjoin(labeldir, im.replace('.jpg', '.txt'))
        open(pjoin(labeldir, annotpath), 'w').write(mylabelsstr)

##########################################################
def plot_venn(labelsclupath, outdir):
    """Plot venn diagram """
    info(inspect.stack()[0][3] + '()')
    df = pd.read_csv(labelsclupath)
    labels = sorted(np.unique(df.label))

    img2id = {}
    for i, img in enumerate(sorted(np.unique(df.img))):
        img2id[img] = i

    subsets = []
    for l in labels:
        aux = df[df.label == l].img.tolist()
        partition = [img2id[k] for k in aux]
        subsets.append(set(partition))

    # edgecolours = ['#993333', '#339933', '#3366ff']
    plt.figure(figsize=(4,3))
    # cl = [[167/255, 167/255, 167/255, 1.0]] * 3
    cl = [[114/255, 105/255, 121/255, 1.0]] * 3
    
    matplotlib_venn.venn3(subsets,
            set_labels = ('TypeA', 'TypeB', 'TypeC'),
            # set_colors=palettehex3[6:],
            set_colors=cl,
            alpha=.7,
            )
    plt.tight_layout()
    plt.savefig(pjoin(outdir, 'counts_venn.pdf'))


#########################################################
def plot_stacked_bar_types(results, nclusters, nlabels,
        colours, outdir):
    """Plot each row of result as a horiz stacked bar plot"""
    fig, ax = plt.subplots(figsize=(5, 4))
    n, m = results.shape

    letters = 'ABCDE'
    rownames = [ 'C{}'.format(i+1) for i in range(nclusters)]
    colnames = [ 'Type {}'.format(letters[i]) for i in range(nlabels)]

    prev = np.zeros(n)
    ps = []
    for j in range(m):
        p = ax.barh(range(n), results[:, j], left=prev, height=.6,
                color=colours[6+j])
        prev += results[:, j]
        ps.append(p)

    ax.set_yticks(np.arange(n))
    ax.set_yticklabels(rownames)
    ax.grid(False)
    ax.set_xlabel('Ratio')
    xticks = np.array([0, .2, .4, .6, .8, 1.0])
    for spine in ax.spines.values():
        spine.set_edgecolor('dimgray')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_ylabel('Community')
    ax.legend(ps, colnames, ncol=len(colnames), bbox_to_anchor=(0.08, 1),
          loc='lower left') #, fontsize='small')
    plt.tight_layout()
    plt.savefig(pjoin(outdir, 'ratio_bars.pdf'))

##########################################################
def get_ratios_by_community(labelsdf, clusters, normalized=True):
    """Get ratio for each community """
    info(inspect.stack()[0][3] + '()')
    results = np.zeros((len(clusters), len(np.unique(labelsdf.label))))
    for i, cl in enumerate(clusters):
        results[i, :] = labelsdf[labelsdf.cluster == cl]. \
                groupby('label').sum().cluster.values
    if normalized: results = results / np.sum(results, axis=1).reshape(-1, 1)
    return results

##########################################################
def main():
    info(inspect.stack()[0][3] + '()')
    t0 = time.time()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', default='/tmp/out/', help='Output directory')
    args = parser.parse_args()

    if not os.path.isdir(args.outdir): os.mkdir(args.outdir)

    annotdir = './data/20200202-types/20200209-8003_annot/'
    graphmlpath = './data/20200202-types/sp.graphml'
    clupath = './data/20200202-types/20200222-infomap.clu'
    shppath = './data/20200202-types/20200224-shp/'
    cluareaspath = './data/20200202-types/20200222-infomap_areas.csv'
    outlabels = pjoin(args.outdir, 'labels.csv')
    outlabelsclu = 'data/labels_and_clu_nodupls.csv'

    # labelsdf = compile_labels(annotdir, outlabels) # Do this for each annotator
    # labelsdf = parse_infomap_results(graphmlpath, clupath, labelsdf,
            # 'er', outlabelsclu)

    # plot_types(clupath, shppath, outlabelsclu, args.outdir)
    # clus = sorted(np.unique(labelsdf.cluster))
    # lbls = sorted(np.unique(labelsdf.label))
    # results = get_ratios_by_community(labelsdf, clus, normalized=True)
    # plot_stacked_bar_types(results, len(clus), len(lbls),
            # palettehex3, args.outdir)
    # plot_counts_normalized(outlabelsclu, cluareaspath, args.outdir)
    # plot_venn(outlabelsclu, args.outdir)

    info('Elapsed time:{}'.format(time.time()-t0))

##########################################################
if __name__ == "__main__":
    main()

