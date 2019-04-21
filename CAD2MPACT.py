"""
Script that takes in a FreeCAD ActiveDocument and outputs an OpenMC XML Geometry

Basic Algorithm for the whole process:
(1) Query all visible objects using the select_all_visible_objects() method in the FreeCADConsole
(2) Pickle objects
(3) Run CAD2MPACT.py
    (1) Instantiate a Model Object and its parameters
    (2)


Instructions:
(1) Define Geometry in FreeCAD
(2) In the FreeCAD Python console add the following loc:
    import sys
    import os
    sys.path.append(os.path.abspath("(path to CAD2MC.py)"))
    import CAD2MC

    *  '/Users/faryab/Documents/UM Academics/UROP 2018-19/Sandbox' in my case

Debugging in FreeCAD console:
    from importlib import reload
    import CAD2MC
    CAD2MC = reload(CAD2MC) # if you want to update in FreeCAD and debug through its interpreter

    import pickle
    vis_objs = CAD2MC.select_all_visible_objects()

    fp = open("(path to THIS python interpreted)/shared.pkl", "w")
    pickle.dump(vis_objs, fp)
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
import pickle
from FreeCAD import Base #
from mpactgeometry import *  # Contains the class heirarchy for the geometry in python

# Have to import FREECAD from a separate env into this one.
# in order to have FREECAD actually work, make sure you have
# Python  3.6.0 or 3.6.2 (3.6.7 DOES NOT work and results
# in a seg fault) I have not tested it with 3.6.3-3.3.6 so far.

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
    area = 0
    # compound object
    if has_outlist(obj):
        sub_objs = obj.OutList

        for sub_obj in sub_objs:
            sub_obj_area = find_area__obj(sub_obj)
            area = sub_obj_area if sub_obj_area > area else area
    else:
        area = find_area_elementary_obj(obj)

    return area


def find_area_elementary_obj(obj):
    """
    Returns the areas of elementary FreeCAD objects
    :param obj:
    :return: area
    """
    print("find_diameter_elementary_obj:") if DEBUG else None

    if "Box" in obj.Name:
        bounds = obj.Shape.BoundBox
        return bounds.XLength * bounds.YLength
    elif "Sphere" in obj.Name:
        print("Error at 'find_area_elementary_obj'. Object not supported for MPACT. ")
        raise NotImplementedError
    elif "Cylinder" in obj.Name:
        bounds = obj.Shape.BoundBox

        # Z-Cylinder
        if abs(bounds.XLength - bounds.YLength) <= 0.001 and abs(bounds.XLength - bounds.ZLength) > 0.001:
            area = math.pi * ((bounds.XLength/2)**2)
            return area
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
    areas = [find_area__obj(obj) for obj in vis_objs]
    sorted_objs = [x for _, x in sorted(zip(areas, vis_objs), key=lambda pair: pair[0], reverse=True)]
    boundary = sorted_objs[0] # 1st element in sorted objs is the biggest
    sorted_objs.pop(0) # remove bound box, since it's not a real level
    bounds = boundary.Shape.BoundBox

    # Create Class Hierarchy using the sorted objects.
    # TODO: Sorted object is a list of COMPOUND OBJS, need elmentary objects.
    # can do something like for each obj -> make_elementary(obj)? ...

    levels = []

    for i in range(start=1, stop=len(sorted_objs)+1):
        lvl = Level(ngeom=1, name=i)
        if "Box" in sorted_objs[i].Name:
            geom = BoxGeom() # TODO
        elif "Cylinder" in sorted_objs[i].Name:
            radius = sorted_objs[i].Radius
            stop_angle = sorted_objs[i].Angle
            centroid = (sorted_objs[i].Placement.Base[0], sorted_objs[i].Placement.Base[1])
            geom = CircleGeom(r=radius, startangl=0, stopangl=stop_angle, centroid=centroid, meshparams=MeshParams())

        lvl.add_geom(geom)
        levels.append(lvl)

    Model = GeneralMeshType(id=1, nlevels=len(vis_objs)-1, xpitch=bounds.XLength,
                            ypitch=bounds.YLength, zpitch=bounds.ZLength, split=0, levels=levels)

    # Export Created Hierarchy to XML

    return Model


def main():
    """
    Main function that emulates the FreeCAD Console

    Currently used for debugging...
    :return:
    """

    fp = open("/Users/faryab/anaconda3/envs/UROPTesting2/bin/shared.pkl")
    vis_objs = pickle.load(fp)

    Model = create_model(vis_objs)

    # TODO: Implement pickle loading then run create_model()

    return


if __name__ == '__main__':
    main()