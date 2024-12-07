from dhybridrpy import dhybridrpy

"""
Todo:
1. Add processing of raw files
2. Implement Dask for lazy loading of large datasets
"""

def main():
    dpy = dhybridrpy(
        "/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/Output",
        "/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/input/input_complex"
    )
    print(dpy.inputs)
    print(dpy.inputs["time"]["niter"])
    print(dpy.inputs["diag_species"])
    print(dpy.timestep(32).fields.Ez(origin="Total").data)
    dpy.timestep(32).fields.Ez(origin="Total").plot()
    # print(dpy.timestep(32).phases.x3x2x1(species=1).data)
    # print(dpy.timestep(32).phases.etx1(species=1).data)
    # print(dpy.timesteps)

if __name__ == "__main__":
    main()