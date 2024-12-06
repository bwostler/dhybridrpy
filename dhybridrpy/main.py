from dhybridrpy import dhybridrpy

"""
Todo:
1. Add processing of raw files
2. Implement Dask for lazy loading of large datasets
"""

def main():
    dhp = dhybridrpy(
        "/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/Output",
        "/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/input/input"
    )
    print(dhp.inputs)
    print(dhp.inputs["time"]["niter"])
    print(dhp.timestep(32).fields.Ez(origin="Total").xlimdata)
    print(dhp.timestep(32).phases.x3x2x1(species=1).data)
    print(dhp.timestep(32).phases.etx1(species=1).data)
    print(dhp.timesteps)

if __name__ == "__main__":
    main()
