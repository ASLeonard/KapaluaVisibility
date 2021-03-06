##common imports
import numpy as np
import matplotlib.pyplot as plt
import glob
import json

##image analysis imports
from scipy import ndimage as ndi
from skimage import io, morphology, measure
from skimage.exposure import histogram
from skimage.filters import sobel

##machine learning imports
from sklearn.cluster import KMeans
from sklearn.svm import SVC, LinearSVC
from sklearn.model_selection import cross_val_score,ShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix

def runAnalysis():
    with open('../data/day_classes.json') as f_in:
        day_classes=json.load(f_in)
        
    ref_im=loadImage(2019,5,5)
    bound=getOceanBoundary(ref_im)
    cols={'good':'dodgerblue','okay':'forestgreen','bad':'firebrick'}
    plt.figure()
    full_features, class_ = [], []
    for im in glob.glob('../data/*.png'):
        ID = im[im.rfind('/')+1:-4]
            
        image= io.imread(im)
        min_y = min(ref_im.shape[1], image.shape[1])
        min_x = min(ref_im.shape[0], image.shape[0])
        new_bound=np.zeros((min_x,min_y),dtype=np.uint8)
        new_bound[:min_x, :min_y] = bound[:min_x,:min_y]

        MI = maskImage(image[:min_x,:min_y],new_bound).astype(float)
        MI[MI==0]=np.nan      
        
        features=[]
        RGB_channels=range(3)
        for i in RGB_channels:
            features.extend([np.nanmedian(MI[...,i]),np.nanvar(MI[...,i])])
            h,hc=getGreyscaleHistogram(maskImage(image[:min_x,:min_y],new_bound),i)
            plt.plot(hc,h,c=cols[day_classes[ID]])
            
        full_features.append(features)
        class_.append(day_classes[ID])
    
    na = np.array(full_features)
    
    ##plot blue channel as example only for KMeans
    f, ax = plt.subplots()
    ax.scatter(*na[...,4:].T,c=[cols[cl_] for cl_ in class_],marker='o',s=80,zorder=100)
    MLAL(na,class_,ax)

    ##run SVM and print out
    print('Mean accuracy {:.3f} ± {:.4f}'.format(*MLSVM(na[...,:],class_,ax)))
    
    plt.show(block=False)
    


def MLSVM(data,classes,ax):
    classes = np.array([1 if c != 'bad' else 0 for c in classes])
    scaler = StandardScaler()
    scaler.fit(data)

    clf = SVC(gamma='scale')
    cv = ShuffleSplit(n_splits=1000, test_size=0.2)
    scores = cross_val_score(clf, data, classes, cv=cv)
   
    return np.mean(scores),np.sqrt(np.var(scores)/len(scores))

    
def MLAL(data,classes,ax):
    k_means = KMeans(n_clusters=2, n_init=50)
    classes=np.array([1 if c!='bad' else 0 for c in classes])
    scaler = StandardScaler()
    scaler.fit(data)
    k_means.fit(data)
    k_means_labels = k_means.labels_
    k_means_cluster_centers = k_means.cluster_centers_
    k_means_labels_unique = np.unique(k_means_labels)

    markers=['s','X','D']
    colors = ['#4EACC5', '#FF9C34', '#4E9A06']
    for k, col in zip(range(2), markers):
        my_members = k_means_labels == k
        cluster_center = k_means_cluster_centers[k]
        plt.plot(data[my_members, 4], data[my_members, 5], 'w', markerfacecolor=None,mec='darkgrey', marker=col,markersize=20,markeredgewidth=3)
    relabel=False
    if relabel:
        ref_classes={K:k_means_labels[list(classes).index(K)] for K in ('good','okay','bad')}
        norm_class=[ref_classes[i] for i in classes]
    else:
        norm_class=classes
    print('Confusion matrix:\n',confusion_matrix(norm_class, k_means_labels))
    
        
def loadImage(year,month,day):
    return io.imread('../data/{}_{:02d}_{:02d}.png'.format(year,month,day))

def maskImage(image, boundary):
    new_image = image.copy()
    for i in range(4):
        new_image[...,i] *= boundary
    return new_image

def getGreyscaleHistogram(image_full,axis=2,plot_it=False):
    image = image_full[...,axis]
    hist, hist_centers = histogram(image,normalize=1)

    ##trim mask out, represented as 0s
    hist=hist[1:]
    hist_centers=hist_centers[1:]

    if plot_it:
        fig, axes = plt.subplots(1, 2, figsize=(8, 3))
        axes[0].imshow(image, cmap=plt.cm.gray, interpolation='nearest')
        axes[0].axis('off')
        axes[1].set_xlabel('channel value',fontsize=18)
        axes[1].set_ylabel('normalised frequency',fontsize=18)
        axes[1].plot(hist_centers, hist, lw=2)
        axes[1].set_title('histogram of gray values')
        fig.suptitle('Blue channel',fontsize=22)
    else:
        return hist, hist_centers


def getOceanBoundary(image_full):
    image = image_full.copy()[...,2]
    elevation_map = sobel(image)

    markers = np.zeros_like(image)
    markers[image < 30] = 1
    markers[image > 150] = 2
    
    segmentation = morphology.watershed(elevation_map, markers)
    segmentation = ndi.binary_fill_holes(segmentation - 1)

    contours = measure.find_contours(segmentation, .8)
    main_contour = sorted(contours, key = len, reverse = True)[0]

    coastal_edge = morphology.remove_small_objects(segmentation,10000)

    fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True)
    axes[0].imshow(image, cmap=plt.cm.gray, interpolation='nearest')
    axes[0].plot(main_contour[:,1], main_contour[:,0], lw=5,c='orange')
    axes[1].imshow(maskImage(image_full, coastal_edge), interpolation='nearest')

    for a in axes:
        a.axis('off')
    fig.suptitle('Coastal Edge detection',fontsize=24)
    plt.tight_layout()
    
    plt.show()
    return coastal_edge


