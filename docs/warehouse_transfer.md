# Traslado de bodega en Siigo PD

## Endpoint

- URL: `https://servicespd.siigo.com/ACEntryApi/api/v1/WarehouseTransfer/Save/`
- Metodo: `POST`
- Autenticacion: header `Authorization` con el `access_token` obtenido desde `BaseSiigoClient`

## Request original capturado

Los ejemplos base viven en:

- `traslado_bodega.js`
- `traslado_bodega.sh`

Esos requests incluian headers de navegador y un payload amplio con metadatos de UI.

### Headers del request original

Entre otros, el request original enviaba:

- `User-Agent`
- `Accept`
- `Accept-Language`
- `content-type`
- `Access-Control-Allow-Origin`
- `Allow`
- `Access-Control-Allow-Methods`
- `Authorization`
- `TransactionId`
- `X-TimeZoneId`
- `traceparent`
- `Origin`
- `Referer`

### Payload original

```json
{
  "Items": [
    {
      "ProductCode": 161151,
      "Description": "COLLAR PRUEBA",
      "LongDescription": "COLLAR PRUEBA",
      "ProductSubType": 0,
      "ProductUnitMeasurement": "94",
      "EntryItemType": 0,
      "Order": 1,
      "CostCenterCode": null,
      "WarehouseCode": 37,
      "DestinationWarehouseCode": -1,
      "AccountCode": 0,
      "SalesmanCode": null,
      "ConceptCode": null,
      "Quantity": 1,
      "Value": 0
    }
  ],
  "AttachFiles": [],
  "EntryType": {
    "ERPDocumentTypeID": 1414,
    "Name": "Nota de traslado entre bodegas",
    "Class": "NT",
    "Code": "NT",
    "IsAutomaticEnum": true,
    "TemplateName": "TransferVoucher",
    "InternalDescription": "",
    "ACAccountCode": -1,
    "UseCostCenter": false,
    "CostCenterDefault": null,
    "CostCenterMandatory": false,
    "AttachmentsFSItemsGUID": null,
    "AllowDecimals": false,
    "IsDiscountValue": false,
    "IsDiscountPercentaje": false,
    "EmailBody": null,
    "EmailHeader": null,
    "EmailCommercialConditions": null
  },
  "Entry": {
    "SalesmanCode": null,
    "DocName": "",
    "DocDate": "20260329",
    "DocNumber": null,
    "CostCenterCode": null,
    "ForeignMoneyCode": null,
    "ExchangeValue": null,
    "ExchangePersonalized": null,
    "Observations": "",
    "AccountCode": 0,
    "ContactCode": null,
    "Header": null,
    "CommercialConditions": null,
    "ACEntryCode": -1,
    "ERPDocumentTypeCode": 1414,
    "IsAllowDecimals": null,
    "AttachmentsFSItemsGUID": ""
  },
  "ModelType": 23
}
```

## Reproduccion y pruning

Para replicar y probar la reduccion se dejo el script:

- `tmp/warehouse_transfer_probe.py`

Ese script:

- autentica con `BaseSiigoClient`
- toma solo `client.authorization`
- reproduce la peticion con `httpx`
- permite comparar perfiles `full`, `trimmed` y `minimal`

## Resultado del pruning

### Headers minimos exitosos

El endpoint funciona solo con:

```json
{
  "Authorization": "<access_token>"
}
```

No fueron necesarios `TransactionId`, `traceparent`, `Origin`, `Referer`, `Accept`, `Accept-Language`, `X-TimeZoneId` ni otros headers de navegador.

### Payload minimo exitoso

El payload minimo que siguio siendo exitoso fue:

```json
{
  "Items": [
    {
      "ProductCode": 161151,
      "WarehouseCode": 37,
      "DestinationWarehouseCode": -1,
      "Quantity": 1
    }
  ],
  "Entry": {
    "DocDate": "20260330"
  }
}
```

## Campos obligatorios confirmados

- `Items[0].ProductCode`
- `Items[0].WarehouseCode`
- `Items[0].DestinationWarehouseCode`
- `Items[0].Quantity`
- `Entry.DocDate`

## Campos descartados en el pruning

Se comprobo que no son necesarios para crear el traslado:

- `EntryType`
- `ModelType`
- `Entry.ERPDocumentTypeCode`
- `Items[0].Description`
- `Items[0].LongDescription`
- `Items[0].ProductSubType`
- `Items[0].ProductUnitMeasurement`
- `Items[0].EntryItemType`
- `Items[0].Order`
- `Items[0].CostCenterCode`
- `Items[0].AccountCode`
- `Items[0].SalesmanCode`
- `Items[0].ConceptCode`
- `Items[0].Value`
- `AttachFiles`
- el resto de campos de `Entry`

## Comportamiento observado

- Exito: responde un JSON escalar con el id del traslado, por ejemplo `1039631`
- Validacion incompleta: puede responder `406` con mensaje de texto plano indicando el campo faltante
- Duplicidad: puede responder `400` con texto plano indicando que ya existe un comprobante equivalente
- Payload demasiado recortado: enviar solo `Items` sin `Entry.DocDate` produjo `500`

## Implementacion final en Python

### Cliente

- `src/siigo/infraestructure/servicespd.py`

Clases agregadas:

- `ServicesPdSiigoModules`
- `ServicesPdSiigoClient`
- `ServicesPdSiigoWarehouseTransferPaths`
- `ServicesPdSiigoWarehouseTransferClient`

Metodo expuesto:

```python
from src.siigo.infraestructure.schema.warehouse_transfer import WarehouseTransferItemSchema

await ServicesPdSiigoWarehouseTransferClient().crear_traslado_bodega(
    fecha=date(2026, 3, 18),
    items=[
        WarehouseTransferItemSchema(
            ProductCode=161151,
            WarehouseCode=37,
            DestinationWarehouseCode=-1,
            Quantity=10,
        )
    ],
)
```

Si `items=[]`, el metodo no envia ninguna peticion y retorna `None`.

### Schemas

- `src/siigo/infraestructure/schema/warehouse_transfer.py`

Schemas agregados:

- `WarehouseTransferHeadersSchema`
- `WarehouseTransferItemSchema`
- `WarehouseTransferEntrySchema`
- `WarehouseTransferPayloadSchema`
- `WarehouseTransferResponseSchema`

`DocDate` se serializa como `YYYYMMDD`.

## Respuesta tipada

La respuesta final del cliente queda normalizada como:

```json
{
  "transfer_id": 1039631
}
```

## Validacion automatizada

Se agregaron pruebas en:

- `test/siigo/warehouse_transfer_test.py`

Y el suite relevante queda pasando con:

```bash
PYTHONPATH=. uv run pytest test/siigo
```
