include "globals.mzn";

% Input parameters (as in data.dzn)
set of int: periods;
array[periods] of float: consumption;
array[periods] of float: estimated_production;
array[periods] of float: buy_price;
array[periods] of float: sell_price;

float: excess_consumption;
float: undersupply_production;

float: soc_min;
float: soc_max;
float: soc_initial;
float: soc_final;

float: charge_efficiency;
float: discharge_efficiency;
float: store_efficiency;
float: charge_cost;

float: shave_sell;
float: shave_charge;
float: shave_discharge;

float: max_buy = 10.0; % Upper bound on grid intake


% Record types definition (templates)
type PeriodPar = record(
  int: id,
  float: cons_eff,
  float: max_prod,
  float: buy_price,
  float: sell_price
);

type PeriodVar = record(
  var 0.0..soc_max: production,
  var 0.0..max_buy: bought,
  var 0.0..shave_sell: sold,
  var 0.0..shave_charge: charge,
  var 0.0..shave_discharge: discharge,
  var soc_min..soc_max: soc,
  var 0..1: is_buying,
  var 0..1: is_selling,
  var 0..1: is_charging,
  var 0..1: is_discharging
);

type Period = PeriodPar ++ PeriodVar;

% instantiation
array[periods] of PeriodPar: periods_par = array1d(periods, [
  (
    id: t,
    cons_eff: consumption[t] + excess_consumption,
    max_prod: max(0.0, estimated_production[t] - undersupply_production),
    buy_price: buy_price[t],
    sell_price: sell_price[t]
  ) | t in periods
]);

array[periods] of PeriodVar: periods_var;

array[periods] of Period: plan = array1d(periods, [
  periods_par[t] ++ periods_var[t] | t in periods
]);






% Constraints

% 1. Max bound on production
constraint forall(t in periods) (
  plan[t].production <= plan[t].max_prod
);

% 2. Grid transaction logic (mutual exclusion & peak shaving)
constraint forall(t in periods) (
  plan[t].is_buying + plan[t].is_selling <= 1 /\
  plan[t].bought <= max_buy * plan[t].is_buying /\
  plan[t].sold <= shave_sell * plan[t].is_selling
);

% 3. Prohibit selling when sell price is negative
constraint forall(t in periods where plan[t].sell_price < 0.0) (
  plan[t].sold == 0.0 /\
  plan[t].is_selling == 0
);

% 4. Battery charging/discharging logic
constraint forall(t in periods) (
  plan[t].is_charging + plan[t].is_discharging <= 1 /\
  plan[t].charge <= shave_charge * plan[t].is_charging /\
  plan[t].discharge <= shave_discharge * plan[t].is_discharging
);

% 5. AC bus power balance
constraint forall(t in periods) (
  plan[t].production + plan[t].discharge + plan[t].bought == 
  plan[t].cons_eff + plan[t].charge + plan[t].sold
);

% 6. Battery state of charge (SoC) dynamics
constraint plan[min(periods)].soc == 
  soc_initial * store_efficiency 
  + plan[min(periods)].charge * charge_efficiency 
  - plan[min(periods)].discharge / discharge_efficiency;

constraint forall(t in periods where t > min(periods)) (
  plan[t].soc == 
    plan[t-1].soc * store_efficiency 
    + plan[t].charge * charge_efficiency 
    - plan[t].discharge / discharge_efficiency
);

% 7. Final SoC terminal target
constraint plan[max(periods)].soc >= soc_final;

% Objective Function
var float: grid_purchase_cost = sum(t in periods) (plan[t].bought * plan[t].buy_price);
var float: battery_wear_cost   = sum(t in periods) (plan[t].charge * charge_cost);
var float: grid_sales_revenue  = sum(t in periods) (plan[t].sold * plan[t].sell_price);

var float: total_cost = grid_purchase_cost + battery_wear_cost - grid_sales_revenue;

solve minimize total_cost;

% Output Formatting
output [
  "OPTIMIZATION SUMMARY\n",
  "Total Cost:         " ++ show_float(10, 4, total_cost) ++ " PLN\n",
  "Grid Purchase Cost: " ++ show_float(10, 4, grid_purchase_cost) ++ " PLN\n",
  "Battery Wear Cost:  " ++ show_float(10, 4, battery_wear_cost) ++ " PLN\n",
  "Grid Export Revenue:" ++ show_float(10, 4, grid_sales_revenue) ++ " PLN\n\n",
  "Period | Demand | Prod   | Bought | Sold   | Charge | Disch  | SoC    \n",
  "-------------------------------------------------------------------------\n"
] ++ [
  format_justify_string(6, 6, show(plan[t].id)) ++ " | " ++
  show_float(6, 3, plan[t].cons_eff) ++ " | " ++
  show_float(6, 3, plan[t].production) ++ " | " ++
  show_float(6, 3, plan[t].bought) ++ " | " ++
  show_float(6, 3, plan[t].sold) ++ " | " ++
  show_float(6, 3, plan[t].charge) ++ " | " ++
  show_float(6, 3, plan[t].discharge) ++ " | " ++
  show_float(6, 3, plan[t].soc) ++ "\n"
  | t in periods
];

% Generating CSV with the solution
output [
  "period,demand,pv_prod,bought,sold,charge,discharge,soc\n"
] ++ [
  "\(plan[t].id),\(plan[t].cons_eff),\(plan[t].production),\(plan[t].bought),\(plan[t].sold),\(plan[t].charge),\(plan[t].discharge),\(plan[t].soc)\n"
  | t in periods
];

