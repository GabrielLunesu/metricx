# Polar: Open Source Payment Infrastructure

Polar is an open source payment infrastructure platform designed for developers to sell SaaS and digital products. It provides a complete monetization solution that handles billing, subscriptions, customer management, benefits delivery, and tax compliance. As a merchant of record, Polar manages the entire payment lifecycle including invoicing, receipts, sales tax, and VAT, allowing developers to focus on building their products while Polar handles the payment infrastructure.

The platform is built as a monorepo with a Python/FastAPI backend, Next.js frontend, and background job processing. It supports multiple pricing models (fixed, usage-based, per-seat, custom), recurring subscriptions, one-time purchases, and integrates with Stripe for payment processing. Polar enables developers to sell access to GitHub repositories, Discord roles, license keys, and custom benefits through a flexible API and SDK. The system includes comprehensive webhooks, customer portals, checkout flows, and analytics dashboards.

## API Endpoints

### List Products

List all products with filtering, pagination, and sorting capabilities. Products can be filtered by organization, archived status, recurring type, and associated benefits.

```bash
# List active products for an organization
curl -X GET "https://api.polar.sh/v1/products/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "is_archived": false,
    "page": 1,
    "limit": 10
  }'

# Response
{
  "items": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440001",
      "name": "Pro Subscription",
      "description": "Access to premium features",
      "is_archived": false,
      "is_recurring": true,
      "recurring_interval": "month",
      "organization_id": "550e8400-e29b-41d4-a716-446655440000",
      "prices": [
        {
          "id": "750e8400-e29b-41d4-a716-446655440002",
          "amount_type": "fixed",
          "price_amount": 2900,
          "price_currency": "usd"
        }
      ],
      "benefits": [
        {
          "id": "850e8400-e29b-41d4-a716-446655440003",
          "type": "discord",
          "description": "Discord Pro Role"
        }
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_count": 1,
    "max_page": 1
  }
}

# Filter by recurring products only
curl -X GET "https://api.polar.sh/v1/products/?organization_id=550e8400-e29b-41d4-a716-446655440000&is_recurring=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Product

Create a new product with pricing configuration and optional benefits. Products can be one-time purchases or recurring subscriptions with various pricing models.

```bash
curl -X POST "https://api.polar.sh/v1/products/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Enterprise Plan",
    "description": "Full access to all features with priority support",
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "is_recurring": true,
    "recurring_interval": "month",
    "prices": [
      {
        "type": "recurring",
        "amount_type": "fixed",
        "price_amount": 9900,
        "price_currency": "usd"
      }
    ],
    "medias": ["media-file-id-1", "media-file-id-2"]
  }'

# Response
{
  "id": "650e8400-e29b-41d4-a716-446655440001",
  "name": "Enterprise Plan",
  "description": "Full access to all features with priority support",
  "is_archived": false,
  "is_recurring": true,
  "recurring_interval": "month",
  "stripe_product_id": "prod_xxxxxxxxxxxxx",
  "organization_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Update Product Benefits

Associate benefits with a product. Benefits are automatically granted to customers when they purchase or subscribe to the product.

```bash
curl -X POST "https://api.polar.sh/v1/products/650e8400-e29b-41d4-a716-446655440001/benefits" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benefits": [
      "850e8400-e29b-41d4-a716-446655440003",
      "850e8400-e29b-41d4-a716-446655440004"
    ]
  }'

# Response
{
  "id": "650e8400-e29b-41d4-a716-446655440001",
  "benefits": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440003",
      "type": "discord",
      "description": "Discord VIP Role"
    },
    {
      "id": "850e8400-e29b-41d4-a716-446655440004",
      "type": "github_repository",
      "description": "Private Repository Access",
      "properties": {
        "repository_owner": "myorg",
        "repository_name": "private-repo"
      }
    }
  ]
}
```

### List Orders

Retrieve order history with advanced filtering by organization, product, customer, discount, and checkout session.

```bash
# List all orders for an organization
curl -X GET "https://api.polar.sh/v1/orders/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "page": 1,
    "limit": 20
  }'

# Response
{
  "items": [
    {
      "id": "950e8400-e29b-41d4-a716-446655440005",
      "amount": 2900,
      "tax_amount": 290,
      "currency": "usd",
      "billing_reason": "purchase",
      "created_at": "2025-01-15T11:00:00Z",
      "customer": {
        "id": "a50e8400-e29b-41d4-a716-446655440006",
        "email": "customer@example.com",
        "name": "John Doe"
      },
      "product": {
        "id": "650e8400-e29b-41d4-a716-446655440001",
        "name": "Pro Subscription"
      },
      "subscription": {
        "id": "b50e8400-e29b-41d4-a716-446655440007",
        "status": "active"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 156,
    "max_page": 8
  }
}

# Filter orders by product billing type
curl -X GET "https://api.polar.sh/v1/orders/?organization_id=550e8400-e29b-41d4-a716-446655440000&product_billing_type=recurring" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Export Orders to CSV

Export order data as CSV for accounting and analytics purposes.

```bash
curl -X GET "https://api.polar.sh/v1/orders/export?organization_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  --output orders.csv

# CSV output columns:
# Order ID, Created At, Amount, Tax Amount, Currency, Customer Email,
# Customer Name, Product Name, Subscription ID, Discount Code
```

### List Subscriptions

Manage recurring subscriptions with filtering by organization, product, customer, and active status.

```bash
# List active subscriptions
curl -X GET "https://api.polar.sh/v1/subscriptions/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "active": true,
    "page": 1,
    "limit": 10
  }'

# Response
{
  "items": [
    {
      "id": "b50e8400-e29b-41d4-a716-446655440007",
      "status": "active",
      "current_period_start": "2025-01-01T00:00:00Z",
      "current_period_end": "2025-02-01T00:00:00Z",
      "cancel_at_period_end": false,
      "amount": 2900,
      "currency": "usd",
      "recurring_interval": "month",
      "customer_id": "a50e8400-e29b-41d4-a716-446655440006",
      "product_id": "650e8400-e29b-41d4-a716-446655440001",
      "price_id": "750e8400-e29b-41d4-a716-446655440002",
      "metadata": {
        "source": "website"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_count": 42,
    "max_page": 5
  }
}

# Filter by specific customer
curl -X GET "https://api.polar.sh/v1/subscriptions/?customer_id=a50e8400-e29b-41d4-a716-446655440006" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Cancel Subscription

Cancel a subscription immediately or at the end of the current billing period.

```bash
curl -X POST "https://api.polar.sh/v1/subscriptions/b50e8400-e29b-41d4-a716-446655440007/cancel" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cancel_at_period_end": true,
    "reason": "customer_request"
  }'

# Response
{
  "id": "b50e8400-e29b-41d4-a716-446655440007",
  "status": "active",
  "cancel_at_period_end": true,
  "canceled_at": "2025-01-15T12:00:00Z",
  "current_period_end": "2025-02-01T00:00:00Z"
}
```

### List Customers

Access customer data with filtering by organization, email, or search query across name and external ID.

```bash
# List all customers
curl -X GET "https://api.polar.sh/v1/customers/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "page": 1,
    "limit": 50
  }'

# Response
{
  "items": [
    {
      "id": "a50e8400-e29b-41d4-a716-446655440006",
      "email": "customer@example.com",
      "name": "John Doe",
      "external_id": "user_12345",
      "tax_id": "US123456789",
      "billing_address": {
        "line1": "123 Main St",
        "city": "San Francisco",
        "state": "CA",
        "postal_code": "94102",
        "country": "US"
      },
      "metadata": {
        "signup_source": "website",
        "plan_tier": "enterprise"
      },
      "created_at": "2024-12-01T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_count": 234,
    "max_page": 5
  }
}

# Search customers by email or name
curl -X GET "https://api.polar.sh/v1/customers/?query=john&organization_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Customer

Create a customer record with optional metadata and billing information.

```bash
curl -X POST "https://api.polar.sh/v1/customers/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newcustomer@example.com",
    "name": "Jane Smith",
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "external_id": "user_67890",
    "metadata": {
      "company": "Acme Corp",
      "employee_count": "50-100"
    },
    "billing_address": {
      "line1": "456 Oak Ave",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "US"
    }
  }'

# Response
{
  "id": "c50e8400-e29b-41d4-a716-446655440008",
  "email": "newcustomer@example.com",
  "name": "Jane Smith",
  "external_id": "user_67890",
  "organization_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "company": "Acme Corp",
    "employee_count": "50-100"
  },
  "created_at": "2025-01-15T13:00:00Z"
}
```

### Export Customers to CSV

Export customer data including billing addresses and metadata for CRM integration.

```bash
curl -X GET "https://api.polar.sh/v1/customers/export?organization_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  --output customers.csv

# CSV columns: ID, External ID, Created At, Email, Name, Tax ID,
# Billing Address (multiple columns), Metadata (JSON)
```

### Create Checkout Session

Create a checkout session for customers to complete purchases with customizable success URLs and metadata.

```bash
curl -X POST "https://api.polar.sh/v1/checkouts/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_price_id": "750e8400-e29b-41d4-a716-446655440002",
    "success_url": "https://example.com/success",
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "metadata": {
      "campaign": "winter_sale",
      "referrer": "partner_site"
    },
    "allow_discount_codes": true
  }'

# Response
{
  "id": "d50e8400-e29b-41d4-a716-446655440009",
  "client_secret": "checkout_secret_xxxxxxxxxxxxx",
  "url": "https://polar.sh/checkout/d50e8400-e29b-41d4-a716-446655440009",
  "status": "open",
  "expires_at": "2025-01-15T15:00:00Z",
  "payment_processor": "stripe",
  "amount": 2900,
  "tax_amount": 290,
  "currency": "usd",
  "product_price": {
    "id": "750e8400-e29b-41d4-a716-446655440002",
    "product_id": "650e8400-e29b-41d4-a716-446655440001"
  }
}

# Embed checkout URL in your app
# User visits: https://polar.sh/checkout/d50e8400-e29b-41d4-a716-446655440009/public/checkout_secret_xxxxxxxxxxxxx
```

### Confirm Checkout Payment

Confirm payment for a checkout session after collecting payment details.

```bash
curl -X POST "https://api.polar.sh/v1/checkouts/d50e8400-e29b-41d4-a716-446655440009/confirm" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_secret": "checkout_secret_xxxxxxxxxxxxx",
    "confirmation_token_id": "stripe_confirmation_token_xxxxx"
  }'

# Response
{
  "id": "d50e8400-e29b-41d4-a716-446655440009",
  "status": "confirmed",
  "customer_id": "a50e8400-e29b-41d4-a716-446655440006",
  "order_id": "950e8400-e29b-41d4-a716-446655440005",
  "subscription_id": "b50e8400-e29b-41d4-a716-446655440007"
}
```

### List Checkout Sessions

View all checkout sessions with filtering by organization, product, customer, and status.

```bash
curl -X GET "https://api.polar.sh/v1/checkouts/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "confirmed",
    "page": 1,
    "limit": 25
  }'

# Response includes checkout sessions with status: open, confirmed, completed, expired
```

### Create Discount

Create discount codes for products with percentage or fixed amount reductions.

```bash
curl -X POST "https://api.polar.sh/v1/discounts/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "code": "WINTER2025",
    "name": "Winter Sale 2025",
    "type": "percentage",
    "basis_points": 2000,
    "products": [
      "650e8400-e29b-41d4-a716-446655440001"
    ],
    "starts_at": "2025-01-01T00:00:00Z",
    "ends_at": "2025-03-31T23:59:59Z",
    "max_redemptions": 100
  }'

# Response
{
  "id": "e50e8400-e29b-41d4-a716-446655440010",
  "code": "WINTER2025",
  "name": "Winter Sale 2025",
  "type": "percentage",
  "amount": 2000,
  "currency": null,
  "redemptions_count": 0,
  "max_redemptions": 100,
  "starts_at": "2025-01-01T00:00:00Z",
  "ends_at": "2025-03-31T23:59:59Z"
}

# Fixed amount discount example
curl -X POST "https://api.polar.sh/v1/discounts/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "code": "SAVE10",
    "name": "$10 Off",
    "type": "fixed",
    "amount": 1000,
    "currency": "usd",
    "products": ["650e8400-e29b-41d4-a716-446655440001"]
  }'
```

### List Discounts

Retrieve all discounts with filtering by organization and name search.

```bash
curl -X GET "https://api.polar.sh/v1/discounts/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "page": 1,
    "limit": 20
  }'

# Response
{
  "items": [
    {
      "id": "e50e8400-e29b-41d4-a716-446655440010",
      "code": "WINTER2025",
      "name": "Winter Sale 2025",
      "type": "percentage",
      "amount": 2000,
      "redemptions_count": 42,
      "max_redemptions": 100
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 8,
    "max_page": 1
  }
}
```

### Create Webhook Endpoint

Set up webhook endpoints to receive real-time event notifications for orders, subscriptions, and customer activities.

```bash
curl -X POST "https://api.polar.sh/v1/webhooks/endpoints" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.example.com/webhooks/polar",
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "events": [
      "order.created",
      "subscription.created",
      "subscription.updated",
      "subscription.canceled",
      "benefit.granted",
      "benefit.revoked"
    ]
  }'

# Response
{
  "id": "f50e8400-e29b-41d4-a716-446655440011",
  "url": "https://api.example.com/webhooks/polar",
  "secret": "whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "events": [
    "order.created",
    "subscription.created",
    "subscription.updated",
    "subscription.canceled",
    "benefit.granted",
    "benefit.revoked"
  ],
  "created_at": "2025-01-15T14:00:00Z"
}

# Webhook payload signature verification
# Use the secret to verify webhook signatures using HMAC SHA-256
```

### List Webhook Events

View webhook event delivery history with filtering and replay capability.

```bash
curl -X GET "https://api.polar.sh/v1/webhooks/events" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "webhook_endpoint_id": "f50e8400-e29b-41d4-a716-446655440011",
    "page": 1,
    "limit": 50
  }'

# Response
{
  "items": [
    {
      "id": "g50e8400-e29b-41d4-a716-446655440012",
      "event_type": "order.created",
      "payload": {
        "type": "order.created",
        "data": {
          "id": "950e8400-e29b-41d4-a716-446655440005",
          "amount": 2900,
          "customer_id": "a50e8400-e29b-41d4-a716-446655440006"
        }
      },
      "last_http_code": 200,
      "last_response": "OK",
      "succeeded_at": "2025-01-15T11:00:05Z",
      "created_at": "2025-01-15T11:00:00Z"
    }
  ]
}
```

### Replay Webhook Event

Manually replay a webhook event for debugging or recovery purposes.

```bash
curl -X POST "https://api.polar.sh/v1/webhooks/events/g50e8400-e29b-41d4-a716-446655440012/replay" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Response: 202 Accepted
# Event will be re-sent to the webhook endpoint
```

## Frontend API Integration

### React Query Hook for Products

Fetch products using TanStack React Query with automatic caching and invalidation.

```typescript
import { useProducts, useCreateProduct } from '@/hooks/queries/products'
import { api, unwrap } from '@polar-sh/client'

// List products in a component
function ProductList({ organizationId }: { organizationId: string }) {
  const { data: products, isLoading } = useProducts(organizationId, {
    is_archived: false,
    page: 1,
    limit: 10,
    sorting: ['-created_at']
  })

  if (isLoading) return <div>Loading...</div>

  return (
    <div>
      {products?.items.map((product) => (
        <div key={product.id}>
          <h3>{product.name}</h3>
          <p>{product.description}</p>
          <p>Price: ${product.prices[0]?.price_amount / 100}</p>
        </div>
      ))}
    </div>
  )
}

// Create a product with automatic cache invalidation
function CreateProductForm({ organization }: { organization: Organization }) {
  const createProduct = useCreateProduct(organization)

  const handleSubmit = async (formData: ProductCreate) => {
    const result = await createProduct.mutateAsync({
      name: formData.name,
      description: formData.description,
      organization_id: organization.id,
      is_recurring: true,
      recurring_interval: 'month',
      prices: [
        {
          type: 'recurring',
          amount_type: 'fixed',
          price_amount: 2900,
          price_currency: 'usd'
        }
      ]
    })

    if (!result.error) {
      // Cache automatically invalidated, product list will refresh
      console.log('Product created:', result.data.id)
    }
  }

  return <form onSubmit={handleSubmit}>...</form>
}

// Direct API call without React Query
async function fetchProduct(productId: string) {
  try {
    const product = await unwrap(
      api.GET('/v1/products/{id}', {
        params: { path: { id: productId } }
      })
    )
    return product
  } catch (error) {
    console.error('Failed to fetch product:', error)
    throw error
  }
}
```

### Subscription Management Hook

Manage subscriptions with filtering and mutations.

```typescript
import { useSubscriptions, useCancelSubscription } from '@/hooks/queries/subscriptions'

function SubscriptionManager({ customerId }: { customerId: string }) {
  const { data: subscriptions } = useSubscriptions({
    customer_id: customerId,
    active: true
  })

  const cancelSubscription = useCancelSubscription()

  const handleCancel = async (subscriptionId: string) => {
    await cancelSubscription.mutateAsync({
      id: subscriptionId,
      cancel_at_period_end: true,
      reason: 'customer_request'
    })
  }

  return (
    <div>
      {subscriptions?.items.map((sub) => (
        <div key={sub.id}>
          <p>Status: {sub.status}</p>
          <p>Amount: ${sub.amount / 100}/{sub.recurring_interval}</p>
          <button onClick={() => handleCancel(sub.id)}>Cancel</button>
        </div>
      ))}
    </div>
  )
}
```

### Checkout Integration

Embed checkout sessions in your application.

```typescript
import { useCreateCheckout } from '@/hooks/queries/checkouts'

function CheckoutButton({ productPriceId }: { productPriceId: string }) {
  const createCheckout = useCreateCheckout()

  const handleCheckout = async () => {
    const result = await createCheckout.mutateAsync({
      product_price_id: productPriceId,
      success_url: 'https://myapp.com/success',
      customer_email: 'customer@example.com',
      metadata: { source: 'app_checkout' }
    })

    if (!result.error) {
      const checkoutUrl = `https://polar.sh/checkout/${result.data.id}/public/${result.data.client_secret}`
      window.location.href = checkoutUrl
    }
  }

  return <button onClick={handleCheckout}>Purchase Now</button>
}
```

## Backend Service Layer

### Product Service

Business logic for product management with authorization checks.

```python
from polar.product.service import product as product_service
from polar.auth.models import AuthSubject

async def create_product_example(session: AsyncSession, auth_subject: AuthSubject):
    """Create a product with service layer."""
    product_create = ProductCreate(
        name="Pro Tier",
        description="Premium features",
        organization_id=org_id,
        is_recurring=True,
        recurring_interval=SubscriptionRecurringInterval.month,
        prices=[
            ProductPriceFixedCreate(
                type="recurring",
                amount_type="fixed",
                price_amount=4900,
                price_currency="usd"
            )
        ]
    )

    product = await product_service.create(
        session=session,
        auth_subject=auth_subject,
        product_create=product_create
    )

    await session.commit()
    return product

async def list_products_example(session: AsyncSession, org_id: UUID):
    """List products with filtering."""
    results, count = await product_service.list(
        session=session,
        auth_subject=auth_subject,
        organization_id=MultipleQueryFilter([org_id]),
        is_archived=False,
        is_recurring=None,
        pagination=PaginationParams(page=1, limit=20),
        sorting=[Sorting(ProductSortProperty.created_at, desc=True)]
    )
    return results, count
```

### Subscription Service

Handle subscription lifecycle and cancellations.

```python
from polar.subscription.service import subscription as subscription_service

async def cancel_subscription_example(
    session: AsyncSession,
    subscription_id: UUID,
    cancel_at_period_end: bool = True
):
    """Cancel a subscription."""
    subscription = await subscription_service.get_by_id(
        session=session,
        auth_subject=auth_subject,
        id=subscription_id
    )

    if not subscription:
        raise ResourceNotFound("Subscription not found")

    updated_subscription = await subscription_service.cancel(
        session=session,
        subscription=subscription,
        cancel_at_period_end=cancel_at_period_end,
        reason="customer_request"
    )

    await session.commit()
    return updated_subscription
```

### Checkout Service

Process checkout sessions and payment confirmations.

```python
from polar.checkout.service import checkout as checkout_service

async def create_checkout_example(
    session: AsyncSession,
    product_price_id: UUID,
    customer_email: str
):
    """Create a checkout session."""
    checkout_create = CheckoutCreate(
        product_price_id=product_price_id,
        customer_email=customer_email,
        success_url="https://example.com/success",
        allow_discount_codes=True,
        metadata={"campaign": "spring_sale"}
    )

    checkout = await checkout_service.create(
        session=session,
        auth_subject=auth_subject,
        checkout_create=checkout_create
    )

    await session.commit()
    return checkout

async def confirm_checkout_example(
    session: AsyncSession,
    checkout_id: UUID,
    confirmation_token_id: str
):
    """Confirm payment for a checkout."""
    checkout = await checkout_service.get_by_id(session, checkout_id)

    confirmed_checkout = await checkout_service.confirm(
        session=session,
        checkout=checkout,
        confirmation_token_id=confirmation_token_id
    )

    await session.commit()
    return confirmed_checkout
```

## Database Models

### Product Model

SQLAlchemy model for products with pricing and benefits relationships.

```python
from polar.models import Product, ProductPrice
from sqlalchemy.orm import Mapped, relationship

class Product(TrialConfigurationMixin, MetadataMixin, RecordModel):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_interval: Mapped[SubscriptionRecurringInterval | None]
    tax_code: Mapped[TaxCode]
    stripe_product_id: Mapped[str | None]
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))

    organization: Mapped["Organization"] = relationship("Organization")
    prices: Mapped[list["ProductPrice"]] = relationship("ProductPrice")
    product_benefits: Mapped[list["ProductBenefit"]] = relationship(
        "ProductBenefit",
        order_by="ProductBenefit.order"
    )

    def get_price(self, id: UUID) -> "ProductPrice | None":
        """Get a specific price by ID."""
        return next((p for p in self.prices if p.id == id), None)

# Query products
async def query_products(session: AsyncSession, org_id: UUID):
    stmt = (
        select(Product)
        .where(Product.organization_id == org_id)
        .where(Product.is_archived == False)
        .options(selectinload(Product.prices))
        .options(selectinload(Product.product_benefits))
    )
    result = await session.execute(stmt)
    return result.scalars().all()
```

### Subscription Model

Model for recurring subscription tracking.

```python
from polar.models import Subscription

class Subscription(RecordModel):
    __tablename__ = "subscriptions"

    status: Mapped[SubscriptionStatus]
    current_period_start: Mapped[datetime]
    current_period_end: Mapped[datetime]
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False)
    canceled_at: Mapped[datetime | None]
    amount: Mapped[int]  # Amount in cents
    currency: Mapped[str]
    recurring_interval: Mapped[SubscriptionRecurringInterval]

    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"))
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    price_id: Mapped[UUID] = mapped_column(ForeignKey("product_prices.id"))
    discount_id: Mapped[UUID | None] = mapped_column(ForeignKey("discounts.id"))

    customer: Mapped["Customer"] = relationship("Customer")
    product: Mapped["Product"] = relationship("Product")
    price: Mapped["ProductPrice"] = relationship("ProductPrice")
```

### Customer Model

Customer data with billing information and metadata.

```python
from polar.models import Customer

class Customer(MetadataMixin, RecordModel):
    __tablename__ = "customers"

    email: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    name: Mapped[str | None]
    external_id: Mapped[str | None] = mapped_column(index=True)
    tax_id: Mapped[str | None]
    billing_address: Mapped[dict | None]  # JSON field

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))

    orders: Mapped[list["Order"]] = relationship("Order")
    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription")
    benefit_grants: Mapped[list["BenefitGrant"]] = relationship("BenefitGrant")
```

## Background Tasks

### Dramatiq Task for Benefit Grant

Asynchronous benefit delivery to customers.

```python
from polar.tasks import actor, TaskPriority

@actor(actor_name="benefit.grant", priority=TaskPriority.MEDIUM)
async def benefit_grant(
    customer_id: UUID,
    benefit_id: UUID,
    order_id: UUID | None = None,
    subscription_id: UUID | None = None
) -> None:
    """Grant a benefit to a customer asynchronously."""
    async with AsyncSession() as session:
        benefit = await benefit_service.get_by_id(session, benefit_id)
        customer = await customer_service.get_by_id(session, customer_id)

        if benefit.type == "discord":
            await discord_service.assign_role(customer, benefit)
        elif benefit.type == "github_repository":
            await github_service.grant_access(customer, benefit)
        elif benefit.type == "license_key":
            await license_key_service.generate_key(customer, benefit)

        await benefit_grant_service.create(
            session=session,
            customer_id=customer_id,
            benefit_id=benefit_id,
            order_id=order_id,
            subscription_id=subscription_id
        )

        await session.commit()

# Enqueue task from endpoint
from polar.tasks import enqueue_task

async def grant_benefits_on_purchase(order: Order):
    """Grant benefits after successful purchase."""
    for benefit in order.product.benefits:
        await enqueue_task(
            "benefit.grant",
            customer_id=order.customer_id,
            benefit_id=benefit.id,
            order_id=order.id
        )
```

## Webhook Event Processing

### Webhook Payload Structure

Standardized webhook event format for all events.

```json
{
  "type": "order.created",
  "data": {
    "id": "950e8400-e29b-41d4-a716-446655440005",
    "amount": 2900,
    "tax_amount": 290,
    "currency": "usd",
    "billing_reason": "purchase",
    "customer": {
      "id": "a50e8400-e29b-41d4-a716-446655440006",
      "email": "customer@example.com"
    },
    "product": {
      "id": "650e8400-e29b-41d4-a716-446655440001",
      "name": "Pro Subscription"
    },
    "subscription": {
      "id": "b50e8400-e29b-41d4-a716-446655440007",
      "status": "active"
    }
  }
}
```

### Webhook Signature Verification

Verify webhook signatures using HMAC SHA-256.

```python
import hmac
import hashlib

def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """Verify webhook signature from Polar."""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)

# Flask/FastAPI webhook handler
from fastapi import Request, HTTPException

@app.post("/webhooks/polar")
async def handle_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Polar-Signature")

    if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()

    if event["type"] == "order.created":
        await handle_order_created(event["data"])
    elif event["type"] == "subscription.canceled":
        await handle_subscription_canceled(event["data"])

    return {"status": "ok"}
```

## Configuration

### Environment Variables

Backend configuration for services and integrations.

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/polar

# Redis
REDIS_URL=redis://localhost:6379/0

# Stripe
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx

# GitHub Integration
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"

# S3 Storage
AWS_S3_BUCKET=polar-uploads
AWS_ACCESS_KEY_ID=xxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxx

# CORS
CORS_ORIGINS=["http://localhost:3000", "https://app.example.com"]

# Application
SECRET=your-secret-key-here
ENVIRONMENT=development
```

### Docker Compose Services

Local development infrastructure setup.

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: polar
      POSTGRES_USER: polar
      POSTGRES_PASSWORD: polar
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: polar
      MINIO_ROOT_PASSWORD: polarstorage
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:

# Start services
# cd server && docker compose up -d
```

### Development Commands

Run the platform locally for development.

```bash
# Backend setup
cd server
uv sync                    # Install Python dependencies
uv run task emails         # Build email templates
uv run task db_migrate     # Run database migrations
uv run task api            # Start API server (port 8000)
uv run task worker         # Start background worker

# Frontend setup
cd clients
pnpm install               # Install Node dependencies
pnpm dev                   # Start Next.js dev server (port 3000)

# Testing
cd server
uv run task test           # Run tests with coverage
uv run task test_fast      # Parallel test execution

cd clients/apps/web
pnpm test                  # Run frontend tests

# Code quality
cd server
uv run task lint           # Auto-fix linting issues
uv run task lint_check     # Check without fixing
uv run task lint_types     # Type checking with mypy

cd clients
pnpm lint                  # Lint frontend code

# Database utilities
cd server
uv run task db_recreate    # Drop and recreate database
uv run task seeds_load     # Load sample data

# Generate API client
cd clients
pnpm generate              # Generate TypeScript client from OpenAPI spec
```

## Summary

Polar provides a comprehensive payment infrastructure that enables developers to monetize their products through flexible pricing models, recurring subscriptions, and one-time purchases. The platform handles the complete payment lifecycle including checkout flows, order management, subscription billing, tax calculation, and invoicing. With built-in support for benefits delivery (Discord roles, GitHub access, license keys), webhook notifications, and customer portals, Polar serves as a complete merchant of record solution.

The REST API follows consistent patterns with pagination, filtering, sorting, and metadata support across all resources. Authentication uses bearer tokens with scope-based authorization, and all endpoints return structured JSON responses with comprehensive error handling. The platform integrates seamlessly with Stripe for payment processing, GitHub for authentication and repository access control, and provides SDKs for JavaScript/TypeScript and Python. Background job processing with Dramatiq enables asynchronous operations like benefit grants and webhook delivery, while the modular architecture allows easy extension and customization.
