# N.Gould 2022
# Based on https://developers.google.com/optimization/bin/bin_packing

from ortools.linear_solver import pywraplp

def auto_nest():

    parts = {
        'p_00001': 1050,
        'p_00002': 500,
        'p_00003': 9000,
        'p_00004': 8500,
        }


    existing_offcuts = {
        'os_00001':450,
        'os_00002':300,
        'os_00003':500,
        }


    new_stock = {
        'ns_00001':10000,
        'ns_00002':10000,
        'ns_00003':10000, 
        'ns_00004':10000,                      
        }


    available_stock = {**existing_offcuts, **new_stock}

    # We want to minimise the requirement to purchase new stock. We therefore assign a value to each piece of stock which we can use to optimise against.
    # New stock is given a value equal to it's length, existing offcuts are valued at 0 to prioitise thier use.
    # Solver will minimise the value of the stock used.
    stock_values = {stock_id:0 for stock_id in existing_offcuts}
    stock_values.update(new_stock)


    # Instantiate the solver
    solver = pywraplp.Solver.CreateSolver('SCIP')


    # Map out every single nest options. 
    nest_options = {}
    for part_id in parts:
        for stock_id in available_stock:
            nest_options[(part_id, stock_id)] = solver.IntVar(0, 1, 'nest_option_%s_%s' %(part_id, stock_id))


    # Solver needs to keep track of the stock used to define the objective
    stock_options = {}
    for stock_id in available_stock:
        stock_options[stock_id] = solver.IntVar(0, 1, 'stock_options_%s' %stock_id)



    # For each part, create a constraint that requires that part to be nested in a single piece of stock
    for part_id in parts:
        solver.Add(sum(nest_options[part_id, stock_id] for stock_id in available_stock) == 1)


    # The parts nested in each piece of stock cannot exceed the stock length.
    # @FIXME: Need to add in an allowance for kerf
    for stock_id in available_stock:
        solver.Add(sum(nest_options[(part_id, stock_id)] * parts[part_id] for part_id in parts) <= stock_options[stock_id] * available_stock[stock_id])


    # Objective: minimize the value of the stock used
    # @FIXME: Need to look at further optimising to maximise the consolidation of offcuts.   i.e. prefer longer offcuts to shorter.  This may be simple to do by solving again with a new objective, but constrained by the existing solution?
    solver.Minimize(solver.Sum([stock_options[stock_id] * stock_values[stock_id] for stock_id in available_stock]))


    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        
        stock_count = 0
        stock_length = 0
        part_length = 0

        for stock_id in available_stock:
            length_utilised = 0
            if stock_options[stock_id].solution_value() == 1:
                parts_nested = []
                for part_id in parts:
                    if nest_options[part_id, stock_id].solution_value() == 1:
                        parts_nested.append(part_id)
                        length_utilised += parts[part_id]
                if parts_nested:
                    stock_count += 1
                    stock_length += available_stock[stock_id]
                    print('Stock ID: %s  %smm' %(stock_id, available_stock[stock_id]))
                    print('  Part IDs: %s' %parts_nested)
                    print('  Length Utilised: %smm' %length_utilised)
                    print('  Total Offcut: %smm' %(available_stock[stock_id] - length_utilised))                    
                    print()
        print()
        print('Total Stock lengths used: %s' %stock_count)


    else:
        print('No solution....??? ')
