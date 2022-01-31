# N.Gould 2022
# Based on https://developers.google.com/optimization/bin/bin_packing

from ortools.linear_solver import pywraplp
from nesting_sample_data import sample_parts, sample_existing_offcuts, sample_new_stock

def auto_nest(parts=None, existing_offcuts=None, new_stock=None, kerf_width = None):

    if not parts:
        parts = sample_parts

    if not existing_offcuts:
        existing_offcuts = sample_existing_offcuts

    if not new_stock:
        new_stock = sample_new_stock

    if not kerf_width:
        kerf_width = 2        

    total_part_length = sum(parts[part_id] for part_id in parts)

    available_stock = {**existing_offcuts, **new_stock}

    # We want to minimise the stock used, but we also want to preference using existing stock. We therefore assign a value to each piece of stock which we can use to optimise against.
    # New stock is given a value equal to thier length, existing offcuts are given a value of half thier length to prioitise use.
    # We will set the solver to minimise the value of the stock used.
    stock_values = {stock_id:(existing_offcuts[stock_id]//2) for stock_id in existing_offcuts}
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
    # We need 1 less kerf_width than the number of parts.
    for stock_id in available_stock:
        solver.Add(sum(nest_options[(part_id, stock_id)] * (parts[part_id]+kerf_width) for part_id in parts) - kerf_width <= stock_options[stock_id] * available_stock[stock_id])


    # Objective: minimize the value of the stock used
    # @FIXME: Need to determine whether further optimising is required to maximise the consolidation of offcuts.   
    # i.e. given a variety of solutions with equal minimisation of the stock value, we want to prefer the solution that has the most offcut length consilidated together so they can be used for future cutting requirements
    solver.Minimize(solver.Sum([stock_options[stock_id] * stock_values[stock_id] for stock_id in available_stock]))

    # Set solver timeout in ms
    solver.set_time_limit(5000)


    status = solver.Solve()

    if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:

        status_str = 'Optimal' if status == pywraplp.Solver.OPTIMAL else 'Feasible'
        
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
                        length_remaining = available_stock[stock_id] - length_utilised
                if parts_nested:
                    wastage = round( (length_remaining / available_stock[stock_id]) * 100, 1 )
                    stock_count += 1
                    stock_length += available_stock[stock_id]
                    print('Stock ID: %s  %smm' %(stock_id, available_stock[stock_id]))
                    print('  Part IDs: %s' %parts_nested)
                    print('  Length Utilised: %smm' %length_utilised)
                    print('  Offcut: %smm' %length_remaining) 
                    print('  Wastage: {}%\n\n'.format(wastage))                   

        total_offcuts = stock_length - total_part_length
        total_wastage = round( (total_offcuts / stock_length) * 100, 1 )
        print('Total pieces of stock used: %s' %stock_count)
        print('Total stock length required: %s' %stock_length)
        print('Total parts nested: %s' %len(parts))
        print('Total length of parts nested: %s' %total_part_length)
        print('Total length of offcuts: %s' %total_offcuts)
        print('Total wastage: {}%\n\n'.format(total_wastage))  


        print('Solver Status: %s' %status_str)
        print('Time to solve = %s milliseconds' %solver.WallTime())
        print('Solved in %s iterations' %solver.iterations()) 


    else:
        print('No solution....??? ')

