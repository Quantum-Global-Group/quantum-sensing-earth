import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN

def detect_z_score(grid, threshold=2.5):
    mean=float(np.mean(grid)); std=float(np.std(grid)) or 1.0
    return np.abs((grid-mean)/std) >= threshold

def detect_isolation_forest(grid, contamination=0.05, seed=42):
    h,w=grid.shape; yy,xx=np.mgrid[0:h,0:w]
    features=np.column_stack([xx.ravel(), yy.ravel(), grid.ravel()])
    labels=IsolationForest(contamination=contamination, random_state=seed).fit_predict(features)
    return (labels==-1).reshape(h,w)

def detect_dbscan(grid, eps=0.4, min_samples=5):
    h,w=grid.shape; threshold=np.percentile(np.abs(grid),95); points=np.argwhere(np.abs(grid)>=threshold)
    mask=np.zeros_like(grid, dtype=bool)
    if len(points)==0: return mask
    labels=DBSCAN(eps=eps*max(h,w)/10, min_samples=min_samples).fit_predict(points)
    clustered=points[labels>=0]
    if len(clustered): mask[clustered[:,0], clustered[:,1]]=True
    return mask
