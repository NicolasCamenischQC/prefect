---
description: Prefect REST API for interacting with the Orion orchestration engine and Prefect Cloud.
tags:
    - REST API
    - Orion
    - Prefect Cloud
---

## Overview

The Prefect REST API is hosted by the Orion Server or Prefect Cloud.

A complete reference for the API is available at the bottom of this document.

Additionally, the reference can be viewed by visiting `/docs` of the API server. For example, [http://localhost:4200/docs](http://localhost:4200/docs) if running the API with `prefect orion start`.

## OpenAPI

The Prefect REST API can be fully described with an OpenAPI 3.0 compliant document. [OpenAPI](https://swagger.io/docs/specification/about/) is a standard specification for describing [REST APIs](https://technically.dev/posts/apis-for-the-rest-of-us).

To generate Prefect's complete OpenAPI document, run the following commands in an interactive Python session:

```python
from prefect.orion.api.server import create_app

app = create_app()
openapi_doc = app.openapi()
```

This document allows you to generate your own API client, explore the API using an API inspection tool, or write tests to ensure API compliance.

## REST Guidelines

The Prefect REST API adheres to the following guidelines:

- Collection names are pluralized (e.g., `/flows`, `/runs`)
- We indicate variable placeholders with colons (e.g., `GET /flows/:id`)
- We use snake case for route names (e.g. `GET /task_runs`)
- We avoid nested resources unless there is no possibility of accessing the child resource outside the parent context. For example, we query `/task_runs` with a flow run filter instead of accessing `/flow_runs/:id/task_runs`.
- The API is hosted with an `/api/:version` prefix that (optionally) allows versioning in the future. By convention, we treat that as part of the base URL and do not include that in API examples
- Filtering, sorting, and pagination parameters are provided in the request body of `POST` requests where applicable
    - Pagination parameters are `limit` and `offset`
    - Sorting is specified with a single `sort` parameter
    - See more information on [filtering](#filtering) below
- **HTTP verbs**:
    - `GET`, `PUT` and `DELETE` requests are always idempotent; `POST` and `PATCH` are not guaranteed to be idempotent
    - `GET` requests can not receive information from the request body
    - `POST` requests can receive information from the request body
    - `POST /collection` creates a new member of the collection
    - `GET /collection` lists all members of the collection
    - `GET /collection/:id` gets a specific member of the collection by ID
    - `DELETE /collection/:id` deletes a specific member of the collection
    - `PUT /collection/:id` creates or replaces a specific member of the collection
    - `PATCH /collection/:id` partially updates a specific member of the collection
    - `POST /collection/action` is how we implement non-CRUD actions. For example, to set a flow run's state, we use `POST /flow_runs/:id/set_state`.
    - `POST /collection/action` may also be used for read-only queries. This is to allow us to send complex arguments as body arguments (which often can not be done via GET). Examples include `POST /flow_runs/filter`, `POST /flow_runs/count`, and `POST /flow_runs/history`.

### Filtering

Objects can be filtered by providing filter criteria in the body of a `POST` request. When multiple criteria are specified, logical AND will be applied to the criteria.

Filter criteria are structured as follows

```
{
    "objects": {
        "object_field": {
            "field_operator_": <field_value>
        }
    }
}
```

where

`objects` is the name of the collection to filter over (e.g. `flows`). The collection can be either the object being queried for (e.g. `flows` for `POST /flows/filter`) or a related object (e.g. `flow_runs` for `POST /flows/filter`).

`object_field` is the name of the field over which to filter (e.g. `name` for `flows`). Note that some objects may have nested object fields, such as `{flow_run: {state: {type: {any_: []}}}}`

`field_operator_` is the operator to apply to a field when filtering. Common examples include:

- `any_`: return objects where this field matches any of the following values
- `is_null_`: return objects where this field is or is not null
- `eq_`: return objects where this field is equal to the following value
- `all_`: return objects where this field matches all of the following values
- `before_`: return objects where this datetime field is less than or equal to the following value
- `after_`: return objects where this datetime field is greater than or equal to the following value

For example, to query for flows with the tag `"database"` and failed flow runs, `POST /flows/filter` with the following request body

```
{
    "flows": {
        "tags": {
            "all_": ["database"]
        }
    },
    "flow_runs": {
        "state": {
            "type": {
              "any_": ["FAILED"]
            }
        }
    }
}
```

## Prefect REST API Reference

The following REST API reference was automatically generated using [Swagger UI](https://swagger.io/tools/swagger-ui/).

!!swagger schema.json!!
