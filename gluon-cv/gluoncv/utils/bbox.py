"""Calculate Intersection-Over-Union(IOU) of two bounding boxes."""
from __future__ import division

import numpy as np
import cv2 as cv
import shapely
from shapely.geometry import Polygon, MultiPoint
import numpy.polynomial.chebyshev as chebyshev

def bbox_iou(bbox_a, bbox_b, offset=0):
    """Calculate Intersection-Over-Union(IOU) of two bounding boxes.

    Parameters
    ----------
    bbox_a : numpy.ndarray
        An ndarray with shape :math:`(N, 4)`.
    bbox_b : numpy.ndarray
        An ndarray with shape :math:`(M, 4)`.
    offset : float or int, default is 0
        The ``offset`` is used to control the whether the width(or height) is computed as
        (right - left + ``offset``).
        Note that the offset must be 0 for normalized bboxes, whose ranges are in ``[0, 1]``.

    Returns
    -------
    numpy.ndarray
        An ndarray with shape :math:`(N, M)` indicates IOU between each pairs of
        bounding boxes in `bbox_a` and `bbox_b`.

    """
    if bbox_a.shape[1] < 4 or bbox_b.shape[1] < 4:
        raise IndexError("Bounding boxes axis 1 must have at least length 4")

    tl = np.maximum(bbox_a[:, None, :2], bbox_b[:, :2])
    br = np.minimum(bbox_a[:, None, 2:4], bbox_b[:, 2:4])

    area_i = np.prod(br - tl + offset, axis=2) * (tl < br).all(axis=2)
    area_a = np.prod(bbox_a[:, 2:4] - bbox_a[:, :2] + offset, axis=1)
    area_b = np.prod(bbox_b[:, 2:4] - bbox_b[:, :2] + offset, axis=1)
    
    return area_i / (area_a[:, None] + area_b - area_i)

def polygon_iou(polygon_as, polygon_bs, offset=0):
    """Calculate Intersection-Over-Union(IOU) of two polygons
    
    Parameters
    ----------
    polygon_as : numpy.ndarray
         An ndarray with shape :math'(N, polygon_a_nums, 2)
    polygon_bs : numpy.ndarray
         An ndarray with shape :math'(M, polygon_b_nums, 2)
    offset : float or int, default is 0
        The ``offset`` is used to control the whether the width(or height) is computed as
        (right - left + ``offset``).
        Note that the offset must be 0 for normalized bboxes, whose ranges are in ``[0, 1]``.
    
    Returns
    ------
    numpy.ndarray
        An An ndarray with shape :math:`(N, M)` indicates IOU between each pairs of
        polygons in `polygon_as` and `polygon_bs`.
    This way is not need the points_num is equal 
    """    
    N = polygon_as.shape[0]
    M = polygon_bs.shape[0]
    polygon_ious = np.zeros((N, M))
    for n in range(N):
        polygon_a = polygon_as[n]
        polya = Polygon(polygon_a).convex_hull
        for m in range(M):
            polygon_b = polygon_bs[m]
            polyb = Polygon(polygon_b).convex_hull
            try:
                inter_area = polya.intersection(polyb).area
                union_poly = np.concatenate((polygon_a,polygon_b))
                union_area = MultiPoint(union_poly).convex_hull.area
                if union_area == 0 or inter_area == 0:
                    iou = 0
                else:
                    iou = float(inter_area) / union_area
                polygon_ious[n][m] = iou
            except shapely.geos.TopologicalError:
                print("shapely.geos.TopologicalError occured, iou set to 0")
                polygon_ious[n][m] = 0
                continue
    return polygon_ious

def cheby(coef):
    """
    coef numpy.addary with shape (N , 2*deg+2) such as (N,18), (N,26)
    theta nuumpy.addary with shape (360,)    [-1,1]

    Return numpy.array woth shape (N,360)
    """
    theta = np.linspace(-1, 1, 360)
    coef = coef.T
    r = chebyshev.chebval(theta, coef)
    
    return r

def coef_trans_polygon(coefs, bboxs, centers):
    
    """Reconstruct the Objects Shape Polygons by Coefs and Centers
    Parameters
    ----------
    coefs : numpy.ndarray
         An ndarray with shape :math'(N,2*deg+2)
    bboxs : numpy.ndarray
         An ndarray with shape :math'(N,4)  x1y1x2y2
    centers : numpy.ndarray
         An ndarray with shape :math'(N,2)  xy
         It is the object predicted center.
    
    Return 
    polygons : numpy.ndarray
         An ndarray with shape :math'(N,360,2) 
    """

    bboxs_x1 = bboxs[:, 0].reshape(-1, 1)  # N,1
    bboxs_x2 = bboxs[:, 2].reshape(-1, 1)  # N,1
    bboxs_y1 = bboxs[:, 1].reshape(-1, 1)  # N,1
    bboxs_y2 = bboxs[:, 3].reshape(-1, 1)  # N,1
    bboxsw = np.abs(bboxs_x2 - bboxs_x1)  # N,1
    bboxsh = np.abs(bboxs_y2 - bboxs_y1)  # N,1
    relative_lens = np.sqrt(bboxsw*bboxsw+bboxsh*bboxsh)  # N,1
    center_xs = centers[:, 0].reshape(-1, 1)  # N,1
    center_ys = centers[:, 1].reshape(-1, 1)  # N,1
    rs = cheby(coefs) * relative_lens  # N, 360
    rs = rs.astype(np.float32)       # N, 360
    theta_list = np.arange(359, -1, -1).reshape(1, 360)  # 1, 360
    theta_list = theta_list.repeat(int(rs.shape[0]), axis=0).astype(np.float32)  # N,360
    x, y = cv.polarToCart(rs, theta_list, angleInDegrees=True)  # N,360    N,360
    x = x + center_xs.astype(np.float32)  # N.360
    y = y + center_ys.astype(np.float32)  # N,360
    
    x = np.clip(x, bboxs_x1, bboxs_x2).reshape(-1, 360, 1)  # N,360,1
    y = np.clip(y, bboxs_y1, bboxs_y2).reshape(-1, 360, 1)  # N,360,1
    polygons = np.concatenate((x, y), axis=-1)  # N,360,2
     
    return polygons 
   
def coef_iou(coef_as, coef_bs, bbox_as, bbox_bs, center_as, center_bs):
    """Calculate Intersection-Over-Union(IOU) of two coefs
    Parameters
    ----------
    coef_as : numpy.ndarray
         An ndarray with shape :math'(N,2*deg+2)
    coef_bs : numpy.ndarray
         An ndarray with shape :math'(M,2*deg+2)
    bbox_as : numpy.ndarray
         An ndarray with shape :math'(N,4)  x1y1x2y2
    bbox_bs : numpy.ndarray
         An ndarray with shape :math'(M,4)  x1y1x2y2
    center_as : numpy.ndarray
         An ndarray with shape :math'(N,2)  xy
    center_bs : numpy.ndarray
         An ndarray with shape :math'(M,2)  xy

    Returns
    ------
    numpy.ndarray
        An An ndarray with shape :math:`(N, M)` indicates IOU between each pairs of
        polygons in `coef_as` and coef_bs`.
    """

    polygon_as = coef_trans_polygon(coef_as, bbox_as, center_as)
    polygon_bs = coef_trans_polygon(coef_bs, bbox_bs, center_bs)
    iou = polygon_iou(polygon_as, polygon_bs)
    
    return iou

def coef_polygon_iou(pred_coef_l, pred_center_l, pred_bbox_l, gt_points_xs_l, gt_points_ys_l):
    """Calculate Intersection-Over-Union(IOU) of pred coefs(Reconstructed) and gt polygon points
    Parameters
    ----------
    pred_coef_l : numpy.ndarray
         An ndarray with shape :math'(N,2*deg+2)
    pred_bbox_l : numpy.ndarray
         An ndarray with shape :math'(N,4)  x1y1x2y2
    pred_center_l : numpy.ndarray
         An ndarray with shape :math'(N,2)  xy
    gt_points_xs_l : numpy.ndarray
         An ndarray with shape :math'(M,360)  x1, x2, x3,..., x360
    gt_points_ys_l : numpy.ndarray
         An ndarray with shape :math'(M,360)  y1, y2, y3,..., y360
    
    Returns
    ------
    numpy.ndarray
        An ndarray with shape :math:`(N, M)` indicates IOU between each pairs of
        polygons in `pred coef` and gt polygon points`.
    """

    gt_points_xs_l = gt_points_xs_l.reshape(-1, 360, 1)  # M, 360 ,1
    gt_points_ys_l = gt_points_ys_l.reshape(-1, 360, 1)  # M, 360 ,1
    polygon_bs = np.concatenate((gt_points_xs_l,gt_points_ys_l), axis=-1)  # M, 360 ,2
    polygon_as = coef_trans_polygon(pred_coef_l, pred_bbox_l, pred_center_l)
    iou = polygon_iou(polygon_as, polygon_bs)
    
    return iou

def bbox_xywh_to_xyxy(xywh):
    """Convert bounding boxes from format (x, y, w, h) to (xmin, ymin, xmax, ymax)

    Parameters
    ----------
    xywh : list, tuple or numpy.ndarray
        The bbox in format (x, y, w, h).
        If numpy.ndarray is provided, we expect multiple bounding boxes with
        shape `(N, 4)`.

    Returns
    -------
    tuple or numpy.ndarray
        The converted bboxes in format (xmin, ymin, xmax, ymax).
        If input is numpy.ndarray, return is numpy.ndarray correspondingly.

    """
    if isinstance(xywh, (tuple, list)):
        if not len(xywh) == 4:
            raise IndexError(
                "Bounding boxes must have 4 elements, given {}".format(len(xywh)))
        w, h = np.maximum(xywh[2] - 1, 0), np.maximum(xywh[3] - 1, 0)
        return (xywh[0], xywh[1], xywh[0] + w, xywh[1] + h)
    elif isinstance(xywh, np.ndarray):
        if not xywh.size % 4 == 0:
            raise IndexError(
                "Bounding boxes must have n * 4 elements, given {}".format(xywh.shape))
        xyxy = np.hstack((xywh[:, :2], xywh[:, :2] + np.maximum(0, xywh[:, 2:4] - 1)))
        return xyxy
    else:
        raise TypeError(
            'Expect input xywh a list, tuple or numpy.ndarray, given {}'.format(type(xywh)))

def bbox_xyxy_to_xywh(xyxy):
    """Convert bounding boxes from format (xmin, ymin, xmax, ymax) to (x, y, w, h).

    Parameters
    ----------
    xyxy : list, tuple or numpy.ndarray
        The bbox in format (xmin, ymin, xmax, ymax).
        If numpy.ndarray is provided, we expect multiple bounding boxes with
        shape `(N, 4)`.

    Returns
    -------
    tuple or numpy.ndarray
        The converted bboxes in format (x, y, w, h).
        If input is numpy.ndarray, return is numpy.ndarray correspondingly.

    """
    if isinstance(xyxy, (tuple, list)):
        if not len(xyxy) == 4:
            raise IndexError(
                "Bounding boxes must have 4 elements, given {}".format(len(xyxy)))
        x1, y1 = xyxy[0], xyxy[1]
        w, h = xyxy[2] - x1 + 1, xyxy[3] - y1 + 1
        return (x1, y1, w, h)
    elif isinstance(xyxy, np.ndarray):
        if not xyxy.size % 4 == 0:
            raise IndexError(
                "Bounding boxes must have n * 4 elements, given {}".format(xyxy.shape))
        return np.hstack((xyxy[:, :2], xyxy[:, 2:4] - xyxy[:, :2] + 1))
    else:
        raise TypeError(
            'Expect input xywh a list, tuple or numpy.ndarray, given {}'.format(type(xyxy)))

def bbox_clip_xyxy(xyxy, width, height):
    """Clip bounding box with format (xmin, ymin, xmax, ymax) to specified boundary.

    All bounding boxes will be clipped to the new region `(0, 0, width, height)`.

    Parameters
    ----------
    xyxy : list, tuple or numpy.ndarray
        The bbox in format (xmin, ymin, xmax, ymax).
        If numpy.ndarray is provided, we expect multiple bounding boxes with
        shape `(N, 4)`.
    width : int or float
        Boundary width.
    height : int or float
        Boundary height.

    Returns
    -------
    type
        Description of returned object.

    """
    if isinstance(xyxy, (tuple, list)):
        if not len(xyxy) == 4:
            raise IndexError(
                "Bounding boxes must have 4 elements, given {}".format(len(xyxy)))
        x1 = np.minimum(width - 1, np.maximum(0, xyxy[0]))
        y1 = np.minimum(height - 1, np.maximum(0, xyxy[1]))
        x2 = np.minimum(width - 1, np.maximum(0, xyxy[2]))
        y2 = np.minimum(height - 1, np.maximum(0, xyxy[3]))
        return (x1, y1, x2, y2)
    elif isinstance(xyxy, np.ndarray):
        if not xyxy.size % 4 == 0:
            raise IndexError(
                "Bounding boxes must have n * 4 elements, given {}".format(xyxy.shape))
        x1 = np.minimum(width - 1, np.maximum(0, xyxy[:, 0]))
        y1 = np.minimum(height - 1, np.maximum(0, xyxy[:, 1]))
        x2 = np.minimum(width - 1, np.maximum(0, xyxy[:, 2]))
        y2 = np.minimum(height - 1, np.maximum(0, xyxy[:, 3]))
        return np.hstack((x1, y1, x2, y2))
    else:
        raise TypeError(
            'Expect input xywh a list, tuple or numpy.ndarray, given {}'.format(type(xyxy)))
