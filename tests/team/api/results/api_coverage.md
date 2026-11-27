# API coverage report

| Operation | Called | Status codes hit / documented | Body fields hit / documented | Missing |
|---|---|---|---|---|
| GET /api/v1/order/ | yes | 2/2 | 0/0 | - |
| POST /api/v1/order/ | yes | 5/5 | 4/4 | - |
| GET /api/v1/order/{id}/ | yes | 3/3 | 0/0 | - |
| PATCH /api/v1/order/{id}/ | yes | 5/5 | 1/1 | - |
| DELETE /api/v1/order/{id}/ | yes | 4/4 | 0/0 | - |
| GET /api/v1/user/{user_id}/order/ | yes | 3/3 | 0/0 | - |
| GET /api/v1/book/ | yes | 2/2 | 0/0 | - |
| POST /api/v1/book/ | yes | 4/4 | 3/3 | - |
| GET /api/v1/book/{id}/ | yes | 3/3 | 0/0 | - |
| GET /api/v1/user/ | yes | 3/3 | 0/0 | - |
| POST /api/v1/reservation/ | yes | 4/4 | 1/1 | - |
| POST /api/v1/reservation/{id}/issue/ | yes | 6/6 | 1/1 | - |
| POST /api/v1/reservation/{id}/cancel/ | yes | 5/5 | 1/1 | - |

- **Endpoint+method coverage:** 13/13 = 100%
- **Status-code coverage:** 49/49 = 100%
- **Request-field coverage:** 11/11 = 100%
- **Roles exercised:** alice, anonymous, bob, librarian, reader
- **Total API calls made:** 704
