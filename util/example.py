from ortools.init.python import init
from ortools.linear_solver import pywraplp


def main():
    print("Google OR-Tools version:", init.OrToolsVersion.version_string())

    # Create the linear solver with the GLOP backend.
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        print("Could not create solver GLOP")
        return

    # Create the variables x and y.
    x_var = solver.NumVar(0, 1, "x")
    y_var = solver.NumVar(0, 2, "y")

    print("Number of variables =", solver.NumVariables())

    infinity = solver.infinity()
    # Create a linear constraint, x + y <= 2.
    constraint = solver.Constraint(-infinity, 2, "ct")
    constraint.SetCoefficient(x_var, 1)
    constraint.SetCoefficient(y_var, 1)

    print("Number of constraints =", solver.NumConstraints())

    # Create the objective function, 3 * x + y.
    objective = solver.Objective()
    objective.SetCoefficient(x_var, 3)
    objective.SetCoefficient(y_var, 1)
    objective.SetMaximization()

    print(f"Solving with {solver.SolverVersion()}")
    result_status = solver.Solve()

    print(f"Status: {result_status}")
    if result_status != pywraplp.Solver.OPTIMAL:
        print("The problem does not have an optimal solution!")
        if result_status == pywraplp.Solver.FEASIBLE:
            print("A potentially suboptimal solution was found")
        else:
            print("The solver could not solve the problem.")
            return

    print("Solution:")
    print("Objective value =", objective.Value())
    print("x =", x_var.solution_value())
    print("y =", y_var.solution_value())

    print("Advanced usage:")
    print(f"Problem solved in {solver.wall_time():d} milliseconds")
    print(f"Problem solved in {solver.iterations():d} iterations")


if __name__ == "__main__":
    init.CppBridge.init_logging("basic_example.py")
    cpp_flags = init.CppFlags()
    cpp_flags.stderrthreshold = True
    cpp_flags.log_prefix = False
    init.CppBridge.set_flags(cpp_flags)
    main()