from dhybridrpy import dhybridrpy

"""
Todo:
1. Add processing of raw files
2. Implement Dask for lazy loading of large datasets
"""

def main():
    dpy = dhybridrpy(
        input_file="/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/input/input_complex",
        output_path="/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/Output"
    )
    # print(dpy.inputs)
    # print(dpy.inputs["time"])
    # print(dpy.inputs["diag_species"])
    # print(dpy.timestep(32).fields.Ez(origin="Total").data)
    # dpy.timestep(32).fields.Ez().plot(dpi=200)
    # print(dpy.timestep(32).phases.x3x2x1(species=1).data)
    # print(dpy.timestep(32).phases.p3x1().data)
    print(dpy.timesteps)

    for ts in dpy.timesteps[1:]:
        print(ts)
        dpy.timestep(ts).fields.EIntensity().plot(save_name=f"EIntensity_{ts}.png")

if __name__ == "__main__":
    main()