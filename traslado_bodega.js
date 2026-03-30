await fetch("https://servicespd.siigo.com/ACEntryApi/api/v1/WarehouseTransfer/Save/", {
    "credentials": "include",
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es",
        "content-type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Allow": "GET, POST, OPTIONS, PUT, DELETE",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS, PUT, DELETE",
        "Authorization": "eyJhbGciOiJSUzI1NiIsImtpZCI6IkM3QzFFQTY5M0FCMDREQTM5RkRBNTc3RDc4NTM0NEYxRkI5MDcwQzgiLCJ4NXQiOiJ4OEhxYVRxd1RhT2YybGQ5ZUZORThmdVFjTWciLCJ0eXAiOiJKV1QifQ.eyJleHAiOjE3NzQ5MjE1MDEsIm5iZiI6MTc3NDgzNTEwMSwidmVyIjoiMS4wIiwiaXNzIjoiaHR0cHM6Ly9hY2NvdW50LnNpaWdvLmNvbS8wZTRlZTVlNi03YWU5LTQzYWEtODhkMS05NTAzOWZmYmE3YTQvdjIuMC8iLCJzdWIiOiIwODNlNDBmNS0zMTBlLTQ5MTMtOWFjZC1iZDQwNWExZmYwYzEiLCJhdWQiOiJjMGY5NWQwMC1hNWI3LTRjZmMtYTg0Yy03ZmMxYmUyYTY3MjAiLCJhY3IiOiJiMmNfMWFfY29sX3BkX3Nzb3NpaWdvIiwiaWF0IjoxNzc0ODM1MTAxLCJhdXRoX3RpbWUiOjE3NzQ4MzUxMDAsIm5hbWUiOiJwcm9qZWN0c0BhdGVsaWVyc2lldGUuY29tIiwibWFpbF9zaWlnbyI6InByb2plY3RzQGF0ZWxpZXJzaWV0ZS5jb20iLCJzdG9yYWdlX2tleSI6InByb2plY3RzQGF0ZWxpZXJzaWV0ZS5jb20iLCJjbG91ZF90ZW5hbnRfY29tcGFueV9rZXkiOiJBVEVMSUVSU0lFVEVTQVMiLCJ1c2Vyc19pZCI6IjY4NSIsInRlbmFudF9pZCI6IjB4MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA4NzE0MDUiLCJ1c2VyX2xpY2Vuc2VfdHlwZSI6IjAiLCJwbGFuX3R5cGUiOiIxNCIsInRlbmFudF9zdGF0ZSI6IjEiLCJtdWx0aXRlbmFudF9pZCI6IjExNDAiLCJjb21wYW5pZXMiOiIxIiwiYWNjb3VudGFudCI6ImZhbHNlIiwidGlkIjoiMGU0ZWU1ZTYtN2FlOS00M2FhLTg4ZDEtOTUwMzlmZmJhN2E0IiwiY2xpZW50X2lkIjoiU2lpZ29XZWIiLCJzY29wZSI6IldlYkFQSSxvZmZsaW5lX2FjY2VzcyIsImF0X2hhc2giOiJLSEJZNjFiVnpsaWM4a0hBSnV6eUp3In0.BgGRjWRwa_beMbUSpxx-ZzMcGJpYdAn4LAjoPDfNoB8y5rSFeiK0ZkNNN25jmVTeZxxu714Tsgzw7x45Pv_dIA5dHZsBfffz4caP98sGvI-9JGVWUL9wA9DbavKghEmgOZK6yTVqBunT8wDCaAcQrsscT_KcU-CkI69X8m0nFatyTRtvE_STEm3gOV4caXyajW4OQ_7bXJmcn2pRqlXG2Q_uiPa9VLTs2c7YZZRPAoKkVG8Sa4T8cTFSZRCGhLAE6plKC9JqBbDqPkAqMxADvNEfyRJa5B6ZR-yBo5cXEq9WcHZdjnrpe_W4j40nPrVAEOzyQYGHk-qzTZJSVmtbdg",
        "TransactionId": "1774836172585",
        "X-TimeZoneId": "7",
        "traceparent": "00-b38eeadaed0192015d0f02d868c25868-04eaf43e90ebf464-01",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Priority": "u=0"
    },
    "referrer": "https://siigonube.siigo.com/",
    "body": "{\"Items\":[{\"ProductCode\":161151,\"Description\":\"COLLAR PRUEBA\",\"LongDescription\":\"COLLAR PRUEBA\",\"ProductSubType\":0,\"ProductUnitMeasurement\":\"94\",\"EntryItemType\":0,\"Order\":1,\"CostCenterCode\":null,\"WarehouseCode\":37,\"DestinationWarehouseCode\":-1,\"AccountCode\":0,\"SalesmanCode\":null,\"ConceptCode\":null,\"Quantity\":1,\"Value\":0}],\"AttachFiles\":[],\"EntryType\":{\"ERPDocumentTypeID\":1414,\"Name\":\"Nota de traslado entre bodegas\",\"Class\":\"NT\",\"Code\":\"NT\",\"IsAutomaticEnum\":true,\"TemplateName\":\"TransferVoucher\",\"InternalDescription\":\"\",\"ACAccountCode\":-1,\"UseCostCenter\":false,\"CostCenterDefault\":null,\"CostCenterMandatory\":false,\"AttachmentsFSItemsGUID\":null,\"AllowDecimals\":false,\"IsDiscountValue\":false,\"IsDiscountPercentaje\":false,\"EmailBody\":null,\"EmailHeader\":null,\"EmailCommercialConditions\":null},\"Entry\":{\"SalesmanCode\":null,\"DocName\":\"\",\"DocDate\":\"20260329\",\"DocNumber\":null,\"CostCenterCode\":null,\"ForeignMoneyCode\":null,\"ExchangeValue\":null,\"ExchangePersonalized\":null,\"Observations\":\"\",\"AccountCode\":0,\"ContactCode\":null,\"Header\":null,\"CommercialConditions\":null,\"ACEntryCode\":-1,\"ERPDocumentTypeCode\":1414,\"IsAllowDecimals\":null,\"AttachmentsFSItemsGUID\":\"\"},\"ModelType\":23}",
    "method": "POST",
    "mode": "cors"
});