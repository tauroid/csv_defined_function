Defines a function from CSV files and class definitions

The CSV files are conceptually split into two halves; domain columns and range columns, corresponding to fields of the domain and range dataclasses. At the moment they're not easily distinguished by name, enabling e.g. ClassName_\* prefixes would be a good first improvement.

The mapping specified by the CSV is defined by taking input data as a domain row, getting all domain rows in the CSV that match it, and returning the intersection of the corresponding range rows. Wildcards (\*) match any piece of data (in their column) on the domain side, and when intersecting range rows, are overridden by any actual data.

## Idea

Example; we want to map the following domain concept

| name | species |
|-|-|
| yogi | bear |

using the mapping

| name | species | legs | hat colour |
|-|-|-|-|
| * | bear | 4 | * |
| yogi | * | * | celadon |
| * | trout | 0 | * |

First select all rows where the domain part (under `name`,`species`) matches our input 

| name | species | legs | hat colour |
|-|-|-|-|
| * | bear | 4 | * |
| yogi | * | * | celadon |

collect the corresponding range entries

| legs | hat colour |
|-|-|
| 4 | * |
| * | celadon |

and intersect them

| legs | hat colour |
|-|-|
| 4 | celadon |

### Invalid mapping

It's possible with CSVs to specify a _relation_ that is not a _function_. The code in this repo detects this (the error message has room for improvement). E.g. when defining a function from the "mapping"

| name | species | legs | hat colour |
|-|-|-|-|
| * | bear | 4 | * |
| yogi | bear | 2 | celadon |

The conflict between yogi bear having two legs, and bears in general having four, will be detected before even specifying an input to be mapped. Perhaps an improvement could be some intuitive precedence behaviour (yogi bear is more specific than bear, so takes precedence), but for now any such cases are just flagged and prevent function creation.

## Usage

``` python
from csv_defined_function import CSVDeserialiser, IceCream, IceCreamName, Product, to_function

from pathlib import Path

from itertools import chain

ice_cream_loader = CSVDeserialiser(tuple[IceCream,Product])
# Different parts of the mapping can be specified in different files
flavours = ice_cream_loader.load(Path("./flavours.csv"))
zip_codes = ice_cream_loader.load(Path("./zip_codes.csv"))

ice_cream_to_product = to_function(chain(flavours, zip_codes))

ice_cream_to_product(IceCream(IceCreamName("a","b"), "ants", 1234))
# Product(product_id=*, company='jelly time', jurisdiction_id=4321, reviews='bad')

conflicting_reviews = ice_cream_loader.load(Path("./conflicting_reviews.csv"))

to_function(conflicting_reviews)
# AssertionError: IceCream(full_name=IceCreamName(brand_name=*, edition=*), flavour='vanilla', zip_code=*) and IceCream(full_name=IceCreamName(brand_name='tots', edition=*), flavour='vanilla', zip_code=*) are compatible (overlap) but their respective mappings Product(product_id=*, company=*, jurisdiction_id=*, reviews='good') and Product(product_id=*, company=*, jurisdiction_id=*, reviews='bad') conflict
# I did say the error message could be improved...
```
