"""
Script that takes in a FreeCAD ActiveDocument and outputs an OpenMC XML Geometry

Basic Algorithm for the whole process:
(1) Query all visible objects using the select_all_visible_objects() method in the FreeCADConsole
(3) Run script() from CAD2MPACT.py
    ()

Directions for FreeCAD console:
(1) Define Geometry in FreeCAD
(2) In the FreeCAD Python console add the following loc:
    import sys
    import os
    sys.path.append(os.path.abspath("(path to CAD2MPACT.py <*>)"))
    import CAD2MPACT as c2mp
(3) vis_objs = c2mp.select_all_visible_objects()
(4) script(vis_objs)

    <*>  '/Users/faryab/Documents/UM Academics/UROP 2018-19/Sandbox' in my case
"""

__title__ = "CAD2MPACT.py"
__author__ = "K. Faryab Haye"
__version__ = "00.00"
__date__    = "4/3/2019"


######################################################
# ----------------- LIBRARY IMPORTS ---------------- #
######################################################

import os, sys
DEBUG = True
#FREECADPATH = '/Users/faryab/anaconda3/envs/UROPTesting/lib' #
#sys.path.append(FREECADPATH) #
import FreeCAD #
import FreeCADGui #
import Part  #FreeCAD's Part Workbench #
import math
from FreeCAD import Base #
from mpactgeometry import *  # Contains the class heirarchy for the geometry in python
from lxml import etree # xml library

# Remark: If importing into FreeCAD console, no need to have imports marked with #

######################################################
# --------------- FreeCAD SCRIPTING ---------------- #
######################################################


def select_all_visible_objects():
    """
    - Selects all the visible objects in the FreeCAD Active Document
    :return: List of visble objects
    """

    objs = FreeCAD.ActiveDocument.Objects
    vis_objs = []

    for obj in objs:
        if FreeCADGui.ActiveDocument.getObject(obj.Name).Visibility == True:
            vis_objs.append(obj)

    return vis_objs


def has_outlist(obj):
    """
    - Checks if the passed object contains an 'informative' outlist.
    - informative in the sense that it is non-empty and that our object is as elementary as a
    shape (so not a wire/point/vector/etc but something like a circle)
    :param obj: FreeCAD object instance
    :return: True or False
    """
    if hasattr(obj, 'Shape'):
        if hasattr(obj, 'OutList'):
            if len(obj.OutList) > 0:
                return True

    return False


def find_area__obj(obj):
    """
    Return the area of the given object. If it is a compound object find area recursively.
    :param obj:
    :return: area
    """
    max_area = 0
    # compound object
    if has_outlist(obj):
        sub_objs = obj.OutList

        for sub_obj in sub_objs:
            sub_obj_area, sub_obj = find_area__obj(sub_obj)
            if sub_obj_area > max_area:
                max_area = sub_obj_area
                max_obj = sub_obj
    else:
        max_area, max_obj = find_area_elementary_obj(obj)

    return max_area, max_obj


def find_area_elementary_obj(obj):
    """
    Returns the areas of elementary FreeCAD objects
    :param obj:
    :return: area
    """
    print("find_diameter_elementary_obj:") if DEBUG else None

    if "Box" in obj.Name:
        bounds = obj.Shape.BoundBox
        return bounds.XLength * bounds.YLength, obj
    elif "Sphere" in obj.Name:
        print("Error at 'find_area_elementary_obj'. Object not supported for MPACT. ")
        raise NotImplementedError
    elif "Cylinder" in obj.Name:
        bounds = obj.Shape.BoundBox

        # Z-Cylinder
        if abs(bounds.XLength - bounds.YLength) <= 0.001 and abs(bounds.XLength - bounds.ZLength) > 0.001:
            area = math.pi * ((bounds.XLength/2)**2)
            return area, obj
        # Some other cylinder
        else:
            print("Error at 'find_area_elementary_obj'. Object not supported for MPACT. ")
            raise NotImplementedError
    else:
        print("Error at 'find_area_elementary_obj'. Object not supported for MPACT. ")
        raise NotImplementedError


def create_model(vis_objs):
    """
    Main function of the create_model that runs (3) from the algorithm defined at the top.

    Remark: We assume materials are predefined, since we are only interested in replicating grometry.
    :return: exports to XML the OpenMC representaion of the geometry
    """

    print("Running CAD2MPACT.py ...")

    # sort using python magic
    areas_objs = [find_area__obj(obj) for obj in vis_objs]
    areas_objs.sort(key=lambda tup: tup[0], reverse=True)
    sorted_objs = [obj[1] for obj in areas_objs]

    boundary = sorted_objs[0] # 1st element in sorted objs is the biggest
    sorted_objs.pop(0) # remove bound box, since it's not a real level
    bounds = boundary.Shape.BoundBox

    levels = []
    # Create Class Hierarchy using the sorted objects.
    for i in range(start=1, stop=len(sorted_objs)+1):
        lvl = Level(ngeom=1, name=i)
        if "Box" in sorted_objs[i].Name:
            geom = BoxGeom() # TODO
        elif "Cylinder" in sorted_objs[i].Name:
            radius = sorted_objs[i].Radius
            stop_angle = sorted_objs[i].Angle
            centroid = (sorted_objs[i].Placement.Base[0], sorted_objs[i].Placement.Base[1])
            geom = CircleGeom(r=radius, startangl=0, stopangl=stop_angle, centroid=centroid, meshparams=MeshParams())
        else:
            print("Error at 'create_model(vis_objs)'. Object not supported for MPACT. ")
            raise NotImplementedError

        lvl.add_geom(geom)
        levels.append(lvl)

    Model = GeneralMeshType(id=1, nlevels=len(vis_objs)-1, xpitch=bounds.XLength,
                            ypitch=bounds.YLength, zpitch=bounds.ZLength, split=0, levels=levels)

    # Export Created Hierarchy to XML

    return Model


def generateXML(model, filename=None):
    """
    Takes in a MPACT Class Heirarchical Model and generates XML based on its hierarchy
    :param model:
    :return: saves 'filename.xml' file at a particular directory
    """

    # TODO:
    # Use lxml


    raise NotImplementedError


def script(vis_objs):
    """
    Main function that emulates the FreeCAD Console

    Currently used for debugging...
    :return:
    """
    Model = create_model(vis_objs)

    generateXML(Model)

    return