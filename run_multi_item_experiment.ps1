# Run this from the project root in PowerShell.
# It installs dependencies, optionally creates shared_data_multi_item/, executes M3 multi-item, executes M5 multi-item, then creates a comparison CSV.

$ErrorActionPreference = "Stop"

Write-Host "=== Multi-Item Recommendation Experiment ==="

if (-not (Test-Path "M2_DWH") -and -not (Test-Path "olist_dwh.dump")) {
    Write-Host "ERROR: Please run this script from the project root folder."
    exit 1
}

$pgPassword = Read-Host "Enter PostgreSQL password for user postgres"
$env:PGPASSWORD = $pgPassword

Write-Host "\nInstalling/updating Python requirements..."
python -m pip install -r requirements.txt

if (Test-Path "shared_data") {
    Write-Host "\nCreating filtered raw CSV dataset in shared_data_multi_item/..."
    python scripts/create_multi_item_dataset.py
} else {
    Write-Host "\nshared_data/ not found, so skipping raw CSV filtering."
    Write-Host "This is okay if your notebooks use the PostgreSQL warehouse/views."
}

Write-Host "\nExecuting M3 multi-item association rules notebook..."
python -m jupyter nbconvert --to notebook --execute notebooks/M3_Association_Rules_Multi_Item.ipynb --output M3_Association_Rules_Multi_Item_EXECUTED.ipynb --ExecutePreprocessor.timeout=-1

Write-Host "\nExecuting M5 multi-item recommender notebook..."
python -m jupyter nbconvert --to notebook --execute notebooks/M5_Hybrid_Recommender_Multi_Item.ipynb --output M5_Hybrid_Recommender_Multi_Item_EXECUTED.ipynb --ExecutePreprocessor.timeout=-1

Write-Host "\nCreating full-vs-multi-item comparison..."
python scripts/compare_full_vs_multi_item.py

Write-Host "\nDONE. Check: outputs/m5_multi_item/full_vs_multi_item_comparison.csv"
