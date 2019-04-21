"""
Script that takes in a FreeCAD ActiveDocument and outputs an OpenMC XML Geometry

Basic Algorithm:
(1) Query All Visible Objects in FreeCAD using select_all_visible_objects # DONE
(2) For each object, find out its previous dependencies, iterate through each object's
    dependency tree and perform operations in order. # DONE
    - e.g Cut Box1 Cylinder1
    - e.g Union Sphere1 Box3 ...
   (a) Recursively do a 'post order traversal'
   (b) Combine objects from left and right children
   (c) Return Combined Objects
(3) Create OpenMC Geometry & Export to XML # TODO
   (a) set root (e.g root = openmc.Universe(cells=(fuel, gap, clad, moderator)
   (b) geom = openmc.Geometry(root)
   (c) geom.export_to_xml()


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

__title__ = "CAD2MC.py"
__author__ = "K. Faryab Haye"
__version__ = "00.00"
__date__    = "26/3/2019"


######################################################
# ----------------- LIBRARY IMPORTS ---------------- #
######################################################

import os, sys
OPENMCPATH = '/Users/faryab/anaconda3/envs/UROPTesting2/lib/python3.6/site-packages/'
DEBUG = True
#FREECADPATH = '/Users/faryab/anaconda3/envs/UROPTesting/lib' #
#sys.path.append(FREECADPATH) #
sys.path.append(OPENMCPATH)
import openmc
import FreeCAD
import FreeCADGui #
import Part  #FreeCAD's Part Workbench #
import math
import pickle
from FreeCAD import Base #

# Have to import FREECAD from a separate env into this one.
# in order to have FREECAD actually work, make sure you have
# Python  3.6.0 or 3.6.2 (3.6.7 DOES NOT work and results
# in a seg fault) I have not tested it with 3.6.3-3.3.6 so far.

# Remark: If importing into FreeCAD console, no need to have imports marked with #

######################################################
# --------------- CONVERSION METHODS --------------- #
######################################################

def convert_box(box):
    """
    Converts a Part workbench Box to an OpenMC Cuboid.
    Only works on unrotated boxes (on the cardinal axes) for now
    :param: box
    :return: box halfspace
    """

    bounds = box.BoundBox

    # TODO: Boundary Type how to specify?
    xMin = openmc.XPlane(x0=bounds.XMin, boundary_type='reflective')
    yMin = openmc.YPlane(y0=bounds.YMin, boundary_type='reflective')
    zMin = openmc.ZPlane(z0=bounds.ZMin, boundary_type='reflective')
    xMax = openmc.XPlane(x0=bounds.XMax, boundary_type='reflective')
    yMax = openmc.YPlane(y0=bounds.YMax, boundary_type='reflective')
    zMax = openmc.ZPlane(z0=bounds.ZMax, boundary_type='reflective')

    box = +xMin & -xMax & +yMin & -yMax & +zMin & -zMax

    return box


def convert_plane(plane):
    """
    Converts an arbitrary FreeCAD plane
    to an OpenMC arbitrary plane
    :param: FreeCAD Plane (from Part Workbench)
    :return: OpenMC plane
    """
    # TODO: Is this really needed?

    return 0


def convert_cylinder(clndr):
    """
    Converts an arbitrary FreeCAD cylinder to an arbitrary OpenMC cylinder
    Restrictions: Only cylinders in the X, Y or Z directions work
    :param clndr:
    :return: cylinder half space
    """
    bounds = clndr.BoundBox
    # 0 1 2 3 4 5
    # X Y Z X Y Z
    #result = openmc.ZCylinder(None, 'transmission', 1, 1, 1)

    # Z-Cylinder
    if abs(bounds.XLength - bounds.YLength) <= 0.001 and abs(bounds.XLength - bounds.ZLength) > 0.001:

        x = clndr.Placement.Base.x
        y = clndr.Placement.Base.y
        r = bounds.XLength/2

        z_min = openmc.ZPlane(z0=bounds.ZMin, boundary_type='reflective')
        z_max = openmc.ZPlane(z0=bounds.ZMax, boundary_type='reflective')

        c_MC = openmc.ZCylinder(None, 'transmission', x, y, r)

        result = -c_MC & -z_max & +z_min

    # Y-Cylinder
    elif abs(bounds.XLength - bounds.ZLength) <= 0.001 and abs(bounds.XLength - bounds.YLength) > 0.001:

        x = clndr.Placement.Base.x
        z = clndr.Placement.Base.z
        r = bounds.XLength / 2

        y_min = openmc.YPlane(y0=bounds.YMin, boundary_type='reflective')
        y_max = openmc.YPlane(y0=bounds.YMax, boundary_type='reflective')

        c_MC = openmc.ZCylinder(None, 'transmission', x, z, r)

        result = -c_MC & -y_max & +y_min

    # X-Cylinder
    elif abs(bounds.YLength - bounds.ZLength) <= 0.001 and abs(bounds.YLength - bounds.XLength) > 0.001:

        x = clndr.Placement.Base.x
        y = clndr.Placement.Base.y
        r = bounds.YLength / 2

        x_min = openmc.XPlane(x0=bounds.XMin, boundary_type='reflective')
        x_max = openmc.XPlane(x0=bounds.XMax, boundary_type='reflective')

        c_MC = openmc.ZCylinder(None, 'transmission', x, y, r)

        result = -c_MC & -x_max & +x_min
    # Some XYZ cylinder with height = diameter
    else:
        #TODO
        print("Unexpected Cylinder Type :( \n")
        return

    return result


def convert_sphere(sph):
    """
    Converts an arbitrary FreeCAD sphere into an OpenMC circle
    :param sph:
    :return: openmc.Sphere
    """

    R = sph.Length / (2 * math.pi)

    bounds = sph.BoundBox
    x_shift = bounds.XMin + bounds.XMax
    y_shift = bounds.YMin + bounds.YMax
    z_shift = bounds.ZMin + bounds.ZMax

    return openmc.Sphere(None,'transmission', x_shift, y_shift, z_shift, R)


def convert_object(root):
    """
    Converts Elementary Objects from FreeCAD to OpenMc
    :param root: FreeCAD Object
    :return: OpenMC Object
    """

    print("convert_object:") if DEBUG else None
    print(f"    root.Name = {root.Name}") if DEBUG else None

    if "Box" in root.Name:
        obj = convert_box(root)
    elif "Sphere" in root.Name:
        obj = convert_sphere(root)
    elif "Cylinder" in root.Name:
        obj = convert_cylinder(root)
    else:
        print("Undefined object (root). Error 'hhx@)d*43<'")
        input()

    return obj


######################################################
# --------------- FreeCAD SCRIPTING ---------------- #
######################################################

def select_all_visible_objects():
    """
    Selects all the visible objects in the FreeCAD Active Document
    :return: List of visble objects
    """

    objs = FreeCAD.ActiveDocument.Objects
    vis_objs = []

    for obj in objs:
        if FreeCADGui.ActiveDocument.getObject(obj.Name).Visibility == True:
            vis_objs.append(obj)

    return vis_objs


def combine_object(root, left, right):
    """
    Takes in two OpenMC objects (left and right) and performs an operation based on
    the operation specified in the 'root' FreeCAD object.

    :param root: extract operation to perform
    :param left, right: parameters for the operation to be performed
    :return: combined OpenMC object
    """
    combined = None

    if "Cut" in root.name:
        # REMARK: Do we even need a cut?

        # TODO: What object cuts what?
        # For now we assume that right child is being subtracted FROM left child

        # A \ B = A \cap B^c
        combined = left & ~right
    elif "Fusion" in root.name:
        combined = left | right
    elif "Common" in root.name:
        combined = left & right
    else:
        print("Undefined Combination. Error '3#@jkLo^' ")
        input()

    return combined


def object_to_OpenMC(root):
    """
    Recursively get all subobjects

    Subobjects of objects having a Shape attribute are not included otherwise each
    single feature of the object would be copied. The result is that bodies,
    compounds, and the result of boolean operations will be converted into a
    simple copy of their shape.

    Remark: This assumes that each shape is made up of two sub_shapes at most.
    e.g a cut/union/intersection can be made up of at most two sub_shapes
    """
    # TODOLater: Implement version that takes in FreeCAD objects made up of many sub_objects
    combined = None

    # We do not need an extra copy for children because OutList is already a copy.
    if hasattr(root, 'Group') and root.TypeId != 'App::Part':
        # fcc_prn(o.Label)
        children = root.Group[2].Group
    else:
        children = root.OutList

    left_and_right = []


    print("object_to_OpenMC:") if DEBUG else None
    print(f"    root.Name = {root.Name}") if DEBUG else None

    # Extract left and Right Child

    print("for child in children:") if DEBUG else None
    for child in children:
        print(f"    child.Name: {child.Name}") if DEBUG else None

        if hasattr(child, 'Shape'):
            print(f"    child.Shape: {child.Shape}") if DEBUG else None
            left_and_right.append(child)

    if DEBUG:
        print(f"    len(left_and_right) = {len(left_and_right)}")

    # 'Modified Post Order Traversal'
    if len(left_and_right) == 2:
        # If both left and right child exist
        left = object_to_OpenMC(left_and_right[0])
        right = object_to_OpenMC(left_and_right[1])

        combined = combine_object(root, left, right)
    elif len(left_and_right) == 1:
        # Only left child exists
        combined = object_to_OpenMC(left_and_right[0])
    elif len(left_and_right) == 0:
        # No Children
        combined = convert_object(root)
    else:
        print("undefined behavior at 'k37%3s_' ")
        input()

    return combined


def vis_objs_to_OpenMC(vis_objs=None):
    """
    Main function of the create_model that runs (1) and (2) from the algorithm defined at the top.

    :return: vis_objs_CAD, vis_objs_MC
    """

    # (1) Query All Visible Objects in FreeCAD using select_all_visible_objects

    # If Running on FreeCAD
    #vis_objs_CAD = select_all_visible_objects()

    # If running separate from FreeCAD just use parameter
    vis_objs_CAD = vis_objs

    # (2) For each object, find out its previous dependencies, iterate through each object's
    #     dependency tree and perform operations in order.
    vis_objs_MC = []
    for obj in vis_objs_CAD:
        mc_obj = object_to_OpenMC(obj)
        vis_objs_MC.append(mc_obj)

    return vis_objs_CAD, vis_objs_MC


def script():
    """
    Main function of the create_model that runs (3) from the algorithm defined at the top.

    Remark: We assume materials are predefined, since we are only interested in replicating grometry.
    :return: exports to XML the OpenMC representaion of the geometry
    """

    # Material Definitions
    if True:
        print("Defining Materials...")
        uo2 = openmc.Material(1, "uo2")

        mat = openmc.Material()
        # Add nuclides to uo2
        uo2.add_nuclide('U235', 0.03)
        uo2.add_nuclide('U238', 0.97)
        uo2.add_nuclide('O16', 2.0)

        uo2.set_density('g/cm3', 10.0)

        zirconium = openmc.Material(2, "zirconium")
        zirconium.add_element('Zr', 1.0)
        zirconium.set_density('g/cm3', 6.6)

        water = openmc.Material(3, "h2o")
        water.add_nuclide('H1', 2.0)
        water.add_nuclide('O16', 1.0)
        water.set_density('g/cm3', 1.0)

        water.add_s_alpha_beta('c_H_in_H2O')

        mats = openmc.Materials([uo2, zirconium, water])

        mats = openmc.Materials()
        mats.append(uo2)
        mats += [zirconium, water]

        mats.export_to_xml()

        ## Element Expansion

        water.remove_nuclide('O16')
        water.add_element('O', 1.0)

        mats.export_to_xml()

        ## Enrichment

        uo2_three = openmc.Material()
        uo2_three.add_element('U', 1.0, enrichment=3.0)
        uo2_three.add_element('O', 2.0)
        uo2_three.set_density('g/cc', 10.0)

    # (3) Create OpenMC Geometry & Export to XML # TODO
    print("Running CAD2MC.py...")

    vis_objs_CAD, vis_objs_MC = vis_objs_to_OpenMC()

    # (If Materials are defined...)
    MATS_DEF = True
    if MATS_DEF:
        cells = []

        fuel_region = None
        gap_region = None
        clad_region = None
        water_region = None

        num_objs = len(vis_objs_CAD)
        for i in range(1, num_objs+1):
            if 'fuel' in vis_objs_CAD[i].Label:
                fuel_region = vis_objs_MC[i]
            elif 'gap' in vis_objs_CAD[i].Label:
                gap_region = vis_objs_MC[i]
            elif 'clad' in vis_objs_CAD[i].Label:
                clad_region = vis_objs_MC[i]
            elif 'water' in vis_objs_CAD[i]:
                water_region = vis_objs_MC[i]
            else:
                print("Unrecognized region. Error: 'ajd#*zz/x'")
                input()

        fuel = openmc.Cell(1, 'fuel')
        fuel.fill = uo2
        fuel.region = fuel_region

        gap = openmc.Cell(2, 'air gap')
        gap.region = gap_region

        clad = openmc.Cell(3, 'clad')
        clad.fill = zirconium
        clad.region = clad_region

        moderator = openmc.Cell(4, 'moderator')
        moderator.fill = water
        moderator.region = water_region

    # (If Materials are not defined, assume cells are not filled with anything...)
    else:
        cells = []

        num_objs = len(vis_objs_CAD)
        for i in range(1, num_objs+1):
            cell = openmc.Cell(i, vis_objs_CAD[i].Label)
            cell.region = vis_objs_MC[i]
            cells.append(cell)

    root = openmc.Universe(cells=cells)
    geom = openmc.Geometry(root)
    geom.export_to_xml()

    return 0

def main():
    """
    Main function that emulates the FreeCAD Console

    Currently used for debugging...
    :return:
    """

    fp = open("/Users/faryab/anaconda3/envs/UROPTesting2/bin/shared.pkl")
    vis_objs = pickle.load(fp)

    # DEVELOPMENT HALTED 3/4/19
    # Moving on to CAD2MPACT as it might be a faster way to develop the MPACT XML file

    # TODO: Plan was to pickle the vis_objs in the FreeCAD console and execute the create_model() module using that.
    # TODO: Script Module still needs debugging.


def test_conversions():
    """
    Example Test Suite
    :return: None
    """

    doc = FreeCAD.newDocument()
    box = doc.addObject("Part::Box", "myBox")
    doc.recompute()
    doc.supportedTypes()

    print("Sphere! \n")
    # Create a sphere of r = 5 at (0,0,0)
    sCAD = Part.makeSphere(5)
    sMC = convert_sphere(sCAD)
    print(sMC)


    print("Cylinder! \n")
    # Create a cylinder in the z-direction
    cCAD = Part.makeCylinder(5, 20) # Radius 5, height 20
    cMC = convert_cylinder(cCAD)
    print(cMC)
    # Rotate 90 degrees on the y direction
    cCAD.rotate(Base.Vector(0, 0, 0), Base.Vector(0, 1, 0), 90)
    cMC = convert_cylinder(cCAD)
    print(cMC)

    print("Box \n")
    # Create a box with arbitrary length, width and height
    bCAD = Part.makeBox(5, 10, 15)
    bMC = convert_box(bCAD)
    print(bMC)

    print("Plane \n")
    # Make Plane with length=5, width=5, at [3, 0, 0] facing [0, 1, 0]
    pCAD = Part.makePlane(5, 5, Base.Vector(3, 0, 0), Base.Vector(0, 1, 0))


if __name__ == '__main__':
    main()