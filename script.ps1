#
# ++++++++++++++++++++++++++++++++++++ Part 0 - set variables ++++++++++++++++++++++++++++++++++++
#
$SUB='<<your subscription>>'
$RG='<<your resource group>>'
$LOC='<<your location>>'
$DLSTOR='<<your data lake account>>'
$FUNSTOR='<<your azure function storage account>>'
$SPN='<<your service principal name>>'
$FILE_SYSTEM='<<your data lake file system name>>'
$EMAIL='<<your email address>>'
$FUNNAME='<<your azure function name>>'
$FUNPN='<<your azure function plan>>'
$SPN='<<your service principal name>>' # Optional, only needed for part 4 to test locally

#
# ++++++++++++++++++++++++++++++++++++ Part 1 - Setup Azure Data Lake ++++++++++++++++++++++++++++++++++++
#
# 1. Create resource group
#
az account set --subscription $SUB                 
az group create -n $RG -l $LOC

# 2. Create data lake account
#
az storage account create -n $DLSTOR -g $RG -l $LOC --sku Standard_LRS --kind StorageV2 --enable-hierarchical-namespace true --allow-shared-key-access false

# 3. Add yourself as user to data lake acount
#
$scope="/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/$DLSTOR/blobServices/default"
az role assignment create --role "Storage Blob Data Contributor" --assignee $email --scope $scope 

# 4. Enable soft delete on storage acount
#
az storage account blob-service-properties update -n $DLSTOR -g $RG --enable-delete-retention true --delete-retention-days 7

# 5. Create File System on date lake account
#
az storage container create --account-name $DLSTOR -n $FILE_SYSTEM --auth-mode login

#
# ++++++++++++++++++++++++++++++++++++ Part 2 - Setup event based snapshots creation ++++++++++++++++++++++++++++++++++++
#
# 1. Deploy Event Grid triggered Functions
#
az functionapp plan create -g $RG -n $FUNPN --sku B1 --is-linux true          
az storage account create -n $FUNSTOR -g $RG -l $LOC --sku Standard_LRS --kind StorageV2                   
az functionapp create -n $FUNNAME -g $RG -s $FUNSTOR -p $FUNPN --assign-identity --runtime Python                             
$function_mi=$(az functionapp show -n $FUNNAME -g $RG | ConvertFrom-Json).identity.principalId                             
az role assignment create --assignee $function_mi --role "Storage Blob Data Contributor" --scope $scope                             
func azure functionapp publish $FUNNAME

# 2. Subscribe to event grid
#
$stordlid = "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.Storage/storageaccounts/$DLSTOR"
$endpointid = "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.Web/sites/$FUNNAME/functions/EventGridTriggerCreateSnapshot"
az eventgrid event-subscription create --name storegversion --source-resource-id $stordlid --endpoint-type azurefunction --endpoint $endpointid --included-event-types Microsoft.Storage.BlobCreated

#
# ++++++++++++++++++++++++++++++++++++ Part 3 - deploy recovery solution in Azure Function ++++++++++++++++++++++++++++++++++++
#
# 1. Deploy Function
#
func azure functionapp publish $FUNNAME

# 2. Get function key
#
$code=$(az functionapp keys list -n $FUNNAME -g $RG | ConvertFrom-Json).functionKeys.default

# 3. Create sample folders and files in File System
#
Invoke-RestMethod "https://$FUNNAME.azurewebsites.net/api/orchestrators/OrchestratorInitFileSystem?code=$code&storage_account_name=$DLSTOR&file_system=$FILE_SYSTEM&number_of_folders=2"

# 4. Restore data lake (play around with restore_date in URL to test # four scenarios described in 2.2
#
Invoke-RestMethod "https://$FUNNAME.azurewebsites.net/api/orchestrators/OrchestratorPointInTimeRecovery?code=$code&restore_date=2023-01-20T00:00:00.0000000Z&storage_account_name=$DLSTOR&file_system=$FILE_SYSTEM&number_of_folders=2"

#
# ++++++++++++++++++++++++++++++++++++ Part 4 (optional) deploy recovery solution locally) ++++++++++++++++++++++++++++++++++++
#
# 1. Create Service Principal
#
$spn_response=$(az ad sp create-for-rbac -n $SPN --skip-assignment)                             
$spn_response = $spn_response | ConvertFrom-Json                             
$spn_app_id=$spn_response.appId                             
$spn_key=$spn_response.password                             
$spn_tenant=$spn_response.tenant

# 2. Add service principal as user to data lake acount
#
$scope="/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/$DLSTOR/blobServices/default"
az role assignment create --assignee $spn_app_id --role "Storage Blob Data Contributor" --scope $scope

# 3. Get value of connection string of storage account adhering to Azure function
#
$AzureWebJobsStorage = $(az storage account show-connection-string -n $FUNSTOR -g $RG | ConvertFrom-Json).connectionString

# 4. Change local settings of project
#
# Create a file called local.settings.json and add the following
#{
#    "IsEncrypted": false,
#    "Values": {
#      "AzureWebJobsStorage": "<<value of $AzureWebJobsStorage>>",
#      "FUNCTIONS_WORKER_RUNTIME": "python",
#      "AZURE_CLIENT_ID": "<<value of $spn_app_id>>",
#      "AZURE_CLIENT_SECRET": "<<value of $spn_key>>",
#      "AZURE_TENANT_ID": "<<value of $spn_tenant>>"
#    }
#}

# 5. Run project locally
#
func host start

# 6. Create sample folders and files in File System
#
Invoke-RestMethod "http://localhost:7071/api/orchestrators/OrchestratorInitFileSystem?storage_account_name=$DLSTOR&file_system=$FILE_SYSTEM&number_of_folders=2"

# 7. Restore data lake (play around with restore_date in URL to test # four scenarios described in 2.2
#
Invoke-RestMethod "http://localhost:7071/api/orchestrators/OrchestratorPointInTimeRecovery?restore_date=2021-01-20T00:00:00.0000000Z&storage_account_name=$DLSTOR&file_system=$FILE_SYSTEM&number_of_folders=2"
