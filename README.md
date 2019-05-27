## UROP Project 2018-2019 Khuwaja Faryab Haye

#### The Objective

The objective of the project was to be able to simulate arbitrary geometries in Neutron Transport Codes such as MPACT and OpenMC from a modelling software such as FreeCAD.

#### The Design

We began prototyping designs for how to go about implementing the program. Intuitively Brendan and I knew that it had to be some sort of adapter program between FreeCAD and MPACT, the task was to figure out how it would be structured and what would go into developing it.

Before going into that I want to quickly answer the *why FreeCAD* question: FreeCAD is a very popular open source CAD modelling software which enables access to a thriving community for support and help. Additionally, all of FreeCAD's functionality is built using Python and natively comes with a Python API of it's own. This is the language I use to create the adapter program and another part of *why* factors in later when I talk about OpenMC.

So we had a few components, now we wanted to figure out how to lay them out and connect them. The initial proposal which seemed promising was to develop a program that would take in a FreeCAD model and output an OpenMC XML file. Then, this OpenMC XML file would be converted into an MPACT XML file which would be read in by the second part of the program and finally the MPACT XML file could be simulated through MPACT.

> FreeCAD —> *CAD2MC.py* —> OpenMC XML —> *conversion.py* —> MPACT XML —> MPACT Simualtion

The approach may seem long winded but it did have it's proponents. One advantage of this aproach was that we would be able to do both OpenMC simulation which uses a Monte Carlo Method as well as MPACT which uses more deterministic approache. Another appeal was that OpenMC came built in with it's own open source community and Python API. It seemed like plugging in FreeCAD and OpenMC would be a straight forward task.

#### Prototyping and A Proof of Concept

After all the theory crafting in the Fall semester it was time to get my hands dirty. Referring to the use case diagrams presented to Brendan as a template I began developing the `CAD2MC.py` file. The idea was that someone would create a model in FreeCAD and then using FreeCAD's Python console, pickle the list of all visible objects and then finally run the program. The program would recursively iterate through the list of objects and produce and OpenMC XML representation of the objects.

This was stopped midway when we realized that it may be more efficient to avoid going through OpenMC all together, but I will highlight how far I got nonetheless. Then I will begin talking about the alternative approach we took, which in hindsight would have been a great starting point, but realistically would not have been reasonable to starting point given our limited initial knowledge of the respective programs and their inner workings.

##### CAD2MC.py implementation details

This is the basic high-level algorithm and instructions on how the program was supposed to be used. It is pretty self explanatory:

```
Basic Algorithm:
(1) Query All Visible Objects in FreeCAD using select_all_visible_objects
(2) For each object, find out its previous dependencies, iterate through each object's
    dependency tree and perform operations in order.
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
```

Next, I will go into some of the specifics. The aim is the explain any gaps in the implementation details, I would advise you to have `CAD2MC.py`, the [FreeCAD](https://www.freecadweb.org/wiki/) and [OpenMC](https://openmc.readthedocs.io/en/stable/) documentations open in front of you.



```python
def convert_box(box):
    """
    Converts a Part workbench Box to an OpenMC Cuboid.
    Only works on unrotated boxes (on the cardinal axes) for now
    :param: box
    :return: box halfspace
    """

    bounds = box.BoundBox
    
    xMin = openmc.XPlane(x0=bounds.XMin, boundary_type='reflective')
    yMin = openmc.YPlane(y0=bounds.YMin, boundary_type='reflective')
    zMin = openmc.ZPlane(z0=bounds.ZMin, boundary_type='reflective')
    xMax = openmc.XPlane(x0=bounds.XMax, boundary_type='reflective')
    yMax = openmc.YPlane(y0=bounds.YMax, boundary_type='reflective')
    zMax = openmc.ZPlane(z0=bounds.ZMax, boundary_type='reflective')

    box = +xMin & -xMax & +yMin & -yMax & +zMin & -zMax

    return box
```

- **box**: Here box is an OpenMC [half-space](https://openmc.readthedocs.io/en/stable/pythonapi/generated/openmc.Halfspace.html). It is defined by unary boolean operators that combine to form a volume. You can basically create arbitrarily complex geomtreies using a combination of such operators. 
- **xMin, yMin, etc**: These are OpenMC geometry objects [(details)](https://openmc.readthedocs.io/en/stable/pythonapi/base.html). Other than planes OpenMC also supports other geometries such as spheres and cylinders. 
- **bounds**: This is an attribute of the FreeCAD Shape object. You can use it to extract coordinates and other geometry information as above. 



```Python
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
```

- **objs:** a Python list of FreeCAD objects.
- **vis_objs**: We are only interested in the visible objects. This is because in our CAD model we have a geometry possibly made up of compound objects (e.g. a [Box](https://www.freecadweb.org/wiki/Part_Box) with a [Sphere](https://www.freecadweb.org/wiki/Part_Sphere) cut out of it). The objects that make up this compound object are stored in FreeCAD's [dependency tree](https://www.freecadweb.org/wiki/Std_DependencyGraph) and made invisible in the GUI. We are not interested in classifying them as separate objects for the purposes of our program, but don't fret. The invisible objects are available to us as `.OutList` attributes of the visible FreeCAD objects (you will see this used later).



```python
def object_to_OpenMC(root):
    """
    Recursively get all subobjects

    Subobjects of objects having a Shape attribute are not included otherwise each
    single feature of the object would be copied. The result is that bodies,
    compounds, and the result of boolean operations will be converted into a
    simple copy of their shape.

    Remark: This assumes that each shape is made up of two (elementary) sub_shapes at most.
    e.g a cut/union/intersection can be made up of at most two sub_shapes
    """
    # TODO Future: Implement version that takes in FreeCAD objects made up of many
    # sub_objects
    combined = None

    # We do not need an extra copy for children because OutList is already a copy.
    if hasattr(root, 'Group') and root.TypeId != 'App::Part':
        children = root.Group[2].Group
    else:
        children = root.OutList

    left_and_right = []
    
    # Extract left and Right Child
    for child in children:
        if hasattr(child, 'Shape'):
            left_and_right.append(child)
            # FIX: Wait... does a compound object have a shape attribute? 
            # ANS: Maybe, but for the sake of this proof of concept out sub-objects are only elementary objs such as Shperes and Boxes which DO have a a shape attribute.

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
```

- **hasattr(root, 'Group')**: If some reason our model is not made up of `FreeCAD::Part::` objects we can still extract an outlist. This might be a case when we group a few of our part objects even.
- **OutList**: This is a generic FreeCAD attribute that gives a list of all sub-objects a FreeCAD object is made out of. So a compound object can be made up of Boxes, Cylinders, Spheres (or even more compound objects), Boxes can be made of Wires, Wires can be made up of Points…
- **hasattr(child, 'Shape'):** We are only interested in objects that have a shape attribute. If a subject object has a shape attribute we add it to our recursive list (Boxes are shapes, Lines and Wires are not).



```Python
def script():
    """
    Main function of the create_model that runs (3) from the algorithm defined at the top.

    Remark: We assume materials are predefined, since we are only interested in replicating
    grometry.
    :return: exports to XML the OpenMC representaion of the geometry
    """
    
    # ...
    
    print("Running CAD2MC.py...")
    vis_objs_CAD, vis_objs_MC = vis_objs_to_OpenMC()
    
    # ...
```

This is the main function of the script, it essentially replicates the OpenMC [Modelling a Pin Cell](https://openmc.readthedocs.io/en/stable/examples/pincell.html) tutorial with the key difference being that every time we define geometry it is using the FreeCAD objects instead of creating it in OpenMC itself. Then we export it to XML and ready it for MPACT.

#### Further Prototyping: An Alternative Approach

At this point it was time to figure out how to take OpenMC XML and convert it into the XML readable by MPACT. Here are snippets of both programs XMLs:

##### OpenMC:

```xml
<?xml version='1.0' encoding='utf-8'?>
<geometry>
  <cell id="1" material="1" name="fuel" region="-5 -4 3" universe="2" />
  <cell id="2" material="void" name="air gap" region="-8 -7 6 ~(-5 -4 3)" universe="2" />
  <cell id="3" material="2" name="clad" region="-11 -10 9 ~(-8 -7 6)" universe="2" />
  <cell id="4" material="3" name="moderator" region="12 -15 13 -16 14 -17 ~(-11 -10 9)" universe="2" />
  <surface boundary="reflective" coeffs="-0.5" id="3" type="z-plane" />
  <surface boundary="reflective" coeffs="0.5" id="4" type="z-plane" />
  <surface coeffs="0.0 0.0 0.39" id="5" type="z-cylinder" />
  <surface boundary="reflective" coeffs="-0.5" id="6" type="z-plane" />
  <surface boundary="reflective" coeffs="0.5" id="7" type="z-plane" />
  < ... ></...>
</geometry>
```

##### MPACT

```XML
<?xml version='1.0' encoding='utf-8'?>
<?xml-stylesheet version="1.0" type="text/xsl" href="PL9.xsl"?>
<ParameterList name="GenPinMeshType">
    <Parameter name="ID" type="int" value="1"/>
    <Parameter name="NLevels" type="int" value="3"/>
    <Parameter name="XPitch" type="float" value=""/>
    <Parameter name="YPitch" type="float" value=""/>
    <Parameter name="ZPitch" type="float" value=""/>
    <Parameter name="Split" type="int" value="0"/>
    <ParameterList name="Level 1">
        <Parameter name="nGeom" type="int" value="1"/>
        <ParameterList name="Geom 1">
            <ParameterList name="CircleGeom">
                <Parameter name="Radius" type="float" value=""/>
                <Parameter name="Centroid" type="float" value=""/>
                <Parameter name="StartingAngle" type="float" value=""/>
                <Parameter name="StoppingAngle" type="float" value=""/>
                <ParameterList name="MeshParams">
                    <Parameter name="nRad" type="int" value=""/>
    <...></...>
```

After a little theory crafting the problem became apparent. OpenMC's representaton for the models was completely different from MPACT's representation. OpenMC's Geometry representation is divided into [cells](https://openmc.readthedocs.io/en/stable/pythonapi/generated/openmc.Cell.html) and [surfaces](https://openmc.readthedocs.io/en/stable/pythonapi/generated/openmc.Surface.html), where Cells are composed of specific Materials and Regions defined by half-spaces created by  the surface IDs. In contrast, MPACT doesn't even take Materials into account at this stage. It's geometry is modelled by levels which consist of individual objects or "Geoms" which themselves can potentially contain multiple Shapes such as "CircleGeom" above. 

We realised that going from FreeCAD to MPACT directly would be a much easier process as they operate with much similar representations. FreeCAD's [BoundBox](https://www.freecadweb.org/wiki/Base_API) would essentially serve as the X, Y and Z pitches for MPACT. The NLevels would be the number of visible objects, and so on. Thus began the second iteration of the development process. 

> FreeCAD —> *CAD2MPACT.py* —> MPACT XML —> MPACT Simualtion

##### CAD2MPACT.py implementation details

This is the basic high-level algorithm and instructions on how the program was supposed to be used. Note how it is similar to `CAD2MC.py` but also how it is different. Instead of being run on a separate interpreter, we can run this directly from the FreeCAD console. 

If you are interested in why it was different interpreters to begin with read this paragraph. There was an obscure dependency issue between OpenMC and FreeCAD which I was completely unable to resolve and the only solution I found was to use separate environments for both and import FreeCAD externally into an interpreter already working with OpenMC. More in the comments of `CAD2MC.py`. 

```rust
Basic Algorithm for the whole process:
(1) Query all visible objects using the select_all_visible_objects() method in the FreeCADConsole
(3) Run script() from CAD2MPACT.py

Directions for FreeCAD console:
(1) Define Geometry in FreeCAD
(2) In the FreeCAD Python console add the following loc:
    import sys
    import os
    sys.path.append(os.path.abspath("(path to CAD2MPACT.py <*>)"))
    import CAD2MPACT as c2mp
(3) vis_objs = c2mp.select_all_visible_objects()
(4) c2mp.script(vis_objs)

    <*>  '/Users/faryab/Documents/UM Academics/UROP 2018-19/Sandbox' in my case
```

This is much more simplified compared to `CAD2MC.py`. The grunt of the work is done in the `script()` method which takes the list of FreeCAD objecs and generates the respective MPACT XML. This is done by first generating the model into a Python class heirarchy and then iterating through that using methods from its native `lxml` library to generate the XML. 

```python
def script(vis_objs):
    Model = create_model(vis_objs)
    generateXML(Model)
    return
```

Generating the XML through the created model should be relatively trivial compared to creating the model itself through FreeCAD object list. Lets take a closer look at how `create_model()` works. It would be a good idea to have `xmlTesting.xml` open as you go through this.



```python
def create_model(vis_objs):
    """
    Main function of the create_model that runs (3) from the algorithm defined at the top.
    Remark: We assume materials are predefined, since we are only interested in replicating 
    geometry.
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
            geom = CircleGeom(r=radius, startangl=0, stopangl=stop_angle, centroid=centroid, 															 meshparams=MeshParams())
        else:
            print("Error at 'create_model(vis_objs)'. Object not supported for MPACT. ")
            raise NotImplementedError

        lvl.add_geom(geom)
        levels.append(lvl)

    Model = GeneralMeshType(id=1, nlevels=len(vis_objs)-1, xpitch=bounds.XLength,
                            ypitch=bounds.YLength, zpitch=bounds.ZLength, split=0, 						 													levels=levels)
    # Export Created Hierarchy to XML
    return Model
```

Much like how we recursively iterate through all sub-objects in `CAD2MC.py`, we recurse throught the list and generate the heirarchy as above. 

- **bounds:** used to extract the X, Y and Z pitch from the boundBox of the largest object (The water region in the FreeCAD in the case of the Pin Cell model).
- **geom:** a circle is the only gemoetry model (for MPACT) implemented so far. This was because it was all that was needed to test the Pin Cell model. Due to time constraints I was unable to implement BoxGeom() but it would not be very hard to do so. Refer to the end of the `xmlTesting.xml` file to see an example of what you would have to implement.

The most important task is done at the top when `find_area__obj` is called for each object. The purpose of this function is to distinguish between the different levels that will make up our MPACT geometry. In MPACT, higher levels are above lower levels and we want to replicate that behavior, in order to do so it is essential to find the outermost area of the FreeCAD Objects. A toy example of this would be a circle (fuel region) inside a ring (a clad region). How do we know the clad region is the outer (lower) level and the fuel region is the inner (higher) level? We find the outermost area of the subobjects and compare which one is bigger (subobjects because the ring is composed of a smaller circle the size of the ruel region subtracted from a larger circle composing the outer boundary of the clad region, so we want to compare the area of the bigger circle to the fuel region circle). The bigger area will be the lower level. 

```python
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
```

This function is pretty straight forward. 



```python
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
```

- The only elementary object supported so far is a Z-Cylinder (or a circle). This is due to time restricrions as well as limitations from what is currently supported my MPACT.

##### TODO

The semester approached it's end and I was unable to implement the `generateXML()` method in `script()` but all that requires is an iteration through the class heirarchy in `Model` and that should be it.

#### For the Future

The project has many larger capabilities. From micro level additions such as adding the functionality to model MPACT boxes to micro level additions such as running and adding support for large scale model tranlations on OpenMC and MPACT models. The possibilities are endless. 





