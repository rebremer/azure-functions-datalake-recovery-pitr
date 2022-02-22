$SUB='<<your subscription>>'
$RG='<<your resource group>>'
$LOC='<<your location>>'
$DLSTOR='<<your data lake account>>'
$FUNSTOR='<<your azure function storage account>>'
$SPN='<<your service principal name>>'
$FILE_SYSTEM='<<your data lake file system name>>'
$email='<<your email address>>'
$FUNNAME='<<your azure function name>>'
$FUNPLAN='<<your azure function plan>>'
#
az account set --subscription $SUB
# Resource group
az group create -n $RG -l $LOC
# Create Storage account Data Lake
az storage account create -n $DLSTOR -g $RG -l $LOC --sku Standard_LRS --kind StorageV2 --enable-hierarchical-namespace true --allow-shared-key-access false
$scope="/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/$DLSTOR/blobServices/default"
az role assignment create --role "Storage Blob Data Contributor" --assignee $email --scope $scope
az storage account blob-service-properties update -n $DLSTOR -g $RG --enable-delete-retention true --delete-retention-days 7
# Create File System
az storage container create --account-name $DLSTOR -n $FILE_SYSTEM --auth-mode login
#
# Storage account Azure FUNCTION
az storage account create -n $FUNSTOR -g $RG -l $LOC --sku Standard_LRS --kind StorageV2
#
$spn_response=$(az ad sp create-for-rbac -n $SPN --skip-assignment)
$spn_response = $spn_response | ConvertFrom-Json
$spn_app_id=$spn_response.appId
$spn_key=$spn_response.password
$spn_tenant=$spn_response.tenant
#
az role assignment create --assignee $spn_app_id --role "Storage Blob Data Contributor" --scope $scope
#
$AzureWebJobsStorage = $(az storage account show-connection-string -n $FUNSTOR -g $RG | ConvertFrom-Json).connectionString
#
func host start
Invoke-RestMethod "http://localhost:7071/api/orchestrators/OrchestratorInitFileSystem?storage_account_name=$DLSTOR&file_system=$FILE_SYSTEM&number_of_folders=2"
Invoke-RestMethod "http://localhost:7071/api/orchestrators/OrchestratorPointInTimeRecovery?restore_date=2021-01-20T00:00:00.0000000Z&storage_account_name=$DLSTOR&file_system=$FILE_SYSTEM&number_of_folders=2"
#
# Deploy to function
az functionapp plan create -g $RG -n $FUNPLAN --sku B1 --is-linux true
az functionapp create -n $FUNNAME -g $RG -s $FUNSTOR -p $FUNPLAN --assign-identity --runtime Python
$function_mi=$(az functionapp show -n $FUNNAME -g $RG | ConvertFrom-Json).identity.principalId
az role assignment create --assignee $function_mi --role "Storage Blob Data Contributor" --scope $scope
func azure functionapp publish $FUNNAME
# Subscribe to event grid
$eventgridkey=$(az functionapp keys list -n $FUNNAME -g $RG | ConvertFrom-Json).systemKeys.eventgrid_extension
$eventgridurl= "https://$FUNNAME.azurewebsites.net/runtime/webhooks/EventGrid^^^?functionName=EventGridTriggerCreateSnapshot^^^&code=$eventgridkey"
az eventgrid event-subscription create --name testrb --source-resource-id "/subscriptions/$SUB/resourceGroups/$RG/providers/microsoft.storage/storageaccounts/$DLSTOR" --included-event-types Microsoft.Storage.BlobCreated --endpoint $eventgridurl