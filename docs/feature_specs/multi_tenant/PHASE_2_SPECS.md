# Phase 2: Billing & Monetization Technical Specifications

## Overview

**Duration:** Weeks 5-8  
**Goal:** Add billing and paid plans to the proven multi-tenant foundation from Phase 1  
**Success Criteria:** Free tenants can upgrade to paid plans with automated billing and usage enforcement

## Deliverables

1. Stripe subscription management integration
2. Usage tracking and automated billing system
3. Plan upgrade/downgrade functionality in existing dashboard
4. Usage limit enforcement with soft/hard limits
5. Marketing landing page for paid plans
6. Email notification system for billing events
7. Enhanced admin panel for billing oversight

## Key Changes from Phase 1

**Building on Proven Foundation:**
- Phase 1A/1B delivered working multi-tenant system with free tier
- Phase 2 adds billing layer without disrupting core functionality
- Existing tenant dashboard gets billing UI components added
- Free tier remains available alongside paid plans

## Billing & Subscription Management

### Stripe Integration Service (`backend/core/billing_service.py`)

```python
import stripe
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from backend.core.tenant_service import TenantService
from backend.core.config import Config

@dataclass
class SubscriptionPlan:
    id: str
    name: str
    price_monthly: int  # in cents
    price_yearly: int   # in cents
    features: List[str]
    limits: Dict[str, int]
    stripe_price_id_monthly: str
    stripe_price_id_yearly: str

@dataclass
class BillingUsage:
    tenant_id: int
    period_start: datetime
    period_end: datetime
    queries_used: int
    storage_mb_used: float
    overage_queries: int
    overage_storage_mb: float
    overage_cost_cents: int

class BillingService:
    def __init__(self):
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.tenant_service = TenantService("backend/logs/admin_monitoring.db")
        
        # Define subscription plans
        self.plans = {
            'free': SubscriptionPlan(
                id='free',
                name='Free',
                price_monthly=0,
                price_yearly=0,
                features=['Basic ChatBot', 'Community Support'],
                limits={'queries': 100, 'storage_mb': 10},
                stripe_price_id_monthly='',
                stripe_price_id_yearly=''
            ),
            'starter': SubscriptionPlan(
                id='starter',
                name='Starter',
                price_monthly=2900,  # $29.00
                price_yearly=29000,  # $290.00 (2 months free)
                features=['Custom Branding', 'Email Support', 'Basic Analytics'],
                limits={'queries': 1000, 'storage_mb': 100},
                stripe_price_id_monthly='price_starter_monthly',
                stripe_price_id_yearly='price_starter_yearly'
            ),
            'pro': SubscriptionPlan(
                id='pro',
                name='Pro',
                price_monthly=9900,  # $99.00
                price_yearly=99000,  # $990.00 (2 months free)
                features=['Advanced Analytics', 'Team Management', 'Priority Support', 'Custom Integrations'],
                limits={'queries': 10000, 'storage_mb': 1000},
                stripe_price_id_monthly='price_pro_monthly',
                stripe_price_id_yearly='price_pro_yearly'
            ),
            'enterprise': SubscriptionPlan(
                id='enterprise',
                name='Enterprise',
                price_monthly=0,  # Custom pricing
                price_yearly=0,
                features=['Unlimited Usage', 'Dedicated Support', 'SLA', 'Custom Development'],
                limits={'queries': -1, 'storage_mb': -1},
                stripe_price_id_monthly='',
                stripe_price_id_yearly=''
            )
        }
    
    async def create_customer(self, tenant_id: int, email: str, name: str) -> str:
        """Create Stripe customer for tenant"""
        tenant = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    'tenant_id': str(tenant_id),
                    'tenant_slug': tenant.slug
                }
            )
            
            # Update tenant with Stripe customer ID
            self._update_tenant_stripe_customer_id(tenant_id, customer.id)
            
            return customer.id
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create Stripe customer: {str(e)}")
    
    async def create_subscription(self, tenant_id: int, plan_id: str, billing_cycle: str = 'monthly') -> Dict[str, Any]:
        """Create subscription for tenant"""
        tenant = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        plan = self.plans.get(plan_id)
        if not plan:
            raise ValueError(f"Invalid plan: {plan_id}")
        
        if plan_id == 'free':
            raise ValueError("Cannot create subscription for free plan")
        
        # Get Stripe customer ID or create customer
        stripe_customer_id = await self._get_or_create_stripe_customer(tenant)
        
        try:
            # Create subscription
            price_id = plan.stripe_price_id_monthly if billing_cycle == 'monthly' else plan.stripe_price_id_yearly
            
            subscription = stripe.Subscription.create(
                customer=stripe_customer_id,
                items=[{'price': price_id}],
                metadata={
                    'tenant_id': str(tenant_id),
                    'plan_id': plan_id,
                    'billing_cycle': billing_cycle
                },
                expand=['latest_invoice.payment_intent']
            )
            
            # Store subscription in database
            await self._store_subscription(tenant_id, subscription, plan_id, billing_cycle)
            
            # Update tenant plan
            await self._update_tenant_plan(tenant_id, plan_id)
            
            return {
                'subscription_id': subscription.id,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret,
                'status': subscription.status
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create subscription: {str(e)}")
    
    async def handle_webhook(self, event: Dict[str, Any]) -> bool:
        """Handle Stripe webhook events"""
        event_type = event['type']
        
        handlers = {
            'customer.subscription.created': self._handle_subscription_created,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_cancelled,
            'invoice.payment_succeeded': self._handle_payment_succeeded,
            'invoice.payment_failed': self._handle_payment_failed,
            'customer.subscription.trial_will_end': self._handle_trial_ending
        }
        
        handler = handlers.get(event_type)
        if handler:
            await handler(event['data']['object'])
            return True
        
        return False
    
    async def calculate_usage_charges(self, tenant_id: int, billing_period_start: datetime, billing_period_end: datetime) -> BillingUsage:
        """Calculate overage charges for billing period"""
        tenant = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        plan = self.plans.get(tenant.plan_type)
        if not plan:
            raise ValueError(f"Invalid plan: {tenant.plan_type}")
        
        # Get usage data for billing period
        usage_data = await self._get_usage_for_period(tenant_id, billing_period_start, billing_period_end)
        
        # Calculate overages
        overage_queries = max(0, usage_data['queries'] - plan.limits['queries']) if plan.limits['queries'] > 0 else 0
        overage_storage = max(0, usage_data['storage_mb'] - plan.limits['storage_mb']) if plan.limits['storage_mb'] > 0 else 0
        
        # Pricing: $0.10 per overage query, $1.00 per GB overage storage
        overage_cost_cents = int(overage_queries * 10 + overage_storage * 100)  # Convert GB to cents
        
        return BillingUsage(
            tenant_id=tenant_id,
            period_start=billing_period_start,
            period_end=billing_period_end,
            queries_used=usage_data['queries'],
            storage_mb_used=usage_data['storage_mb'],
            overage_queries=overage_queries,
            overage_storage_mb=overage_storage,
            overage_cost_cents=overage_cost_cents
        )
    
    async def process_monthly_billing(self):
        """Process monthly billing for all active tenants"""
        # Get all active tenants with paid plans
        tenants = self.tenant_service.list_tenants(status='active')
        paid_tenants = [t for t in tenants if t.plan_type not in ['free']]
        
        billing_date = datetime.now().replace(day=1)  # First of current month
        period_start = (billing_date - timedelta(days=1)).replace(day=1)  # First of previous month
        period_end = billing_date - timedelta(days=1)  # Last day of previous month
        
        for tenant in paid_tenants:
            try:
                # Calculate usage and overages
                usage = await self.calculate_usage_charges(tenant.id, period_start, period_end)
                
                if usage.overage_cost_cents > 0:
                    # Create usage-based invoice item
                    await self._create_usage_invoice_item(tenant.id, usage)
                
                # Reset monthly usage counters
                self.tenant_service.update_tenant_usage(
                    tenant.id, 
                    reset_monthly_usage=True
                )
                
            except Exception as e:
                print(f"Error processing billing for tenant {tenant.id}: {str(e)}")
    
    # Private helper methods
    async def _get_or_create_stripe_customer(self, tenant) -> str:
        """Get existing Stripe customer or create new one"""
        # Implementation would check if tenant has stripe_customer_id
        # and create new customer if not
        pass
    
    async def _store_subscription(self, tenant_id: int, subscription: Any, plan_id: str, billing_cycle: str):
        """Store subscription details in database"""
        # Implementation would store in tenant_subscriptions table
        pass
    
    async def _update_tenant_plan(self, tenant_id: int, plan_id: str):
        """Update tenant's plan type"""
        # Implementation would update tenants table
        pass
    
    # Additional webhook handlers
    async def _handle_subscription_created(self, subscription: Dict[str, Any]):
        """Handle subscription creation"""
        pass
    
    async def _handle_payment_succeeded(self, invoice: Dict[str, Any]):
        """Handle successful payment"""
        pass
    
    async def _handle_payment_failed(self, invoice: Dict[str, Any]):
        """Handle failed payment - send notification, suspend if needed"""
        pass
```

### Enhanced Database Schema

```sql
-- Add billing-related tables

CREATE TABLE tenant_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(255) NOT NULL,
    plan_id VARCHAR(50) NOT NULL,
    billing_cycle VARCHAR(20) NOT NULL, -- 'monthly' or 'yearly'
    status VARCHAR(50) NOT NULL, -- 'active', 'cancelled', 'past_due', 'unpaid'
    current_period_start DATETIME NOT NULL,
    current_period_end DATETIME NOT NULL,
    trial_end DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT chk_billing_cycle CHECK (billing_cycle IN ('monthly', 'yearly')),
    CONSTRAINT chk_subscription_status CHECK (status IN ('active', 'cancelled', 'past_due', 'unpaid', 'trialing'))
);

CREATE TABLE tenant_usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    record_date DATE NOT NULL,
    queries_count INTEGER DEFAULT 0,
    storage_mb REAL DEFAULT 0.0,
    api_calls_count INTEGER DEFAULT 0,
    bandwidth_gb REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE(tenant_id, record_date)
);

CREATE TABLE billing_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    stripe_invoice_id VARCHAR(255) UNIQUE NOT NULL,
    amount_cents INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'paid', 'open', 'void', 'uncollectible'
    billing_period_start DATETIME NOT NULL,
    billing_period_end DATETIME NOT NULL,
    overage_charges_cents INTEGER DEFAULT 0,
    invoice_pdf_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Add Stripe customer ID to tenants table
ALTER TABLE tenants ADD COLUMN stripe_customer_id VARCHAR(255);
CREATE INDEX idx_tenants_stripe_customer ON tenants(stripe_customer_id);
```

## Tenant Onboarding System

### Onboarding Service (`backend/core/onboarding_service.py`)

```python
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import secrets
import os
from backend.core.tenant_service import TenantService
from backend.core.billing_service import BillingService
from backend.core.email_service import EmailService

@dataclass
class OnboardingStep:
    id: str
    name: str
    description: str
    status: str  # 'pending', 'in_progress', 'completed', 'skipped'
    required: bool
    order: int

@dataclass
class OnboardingProgress:
    tenant_id: int
    steps: List[OnboardingStep]
    current_step: str
    completion_percentage: int
    started_at: datetime
    completed_at: Optional[datetime]

class OnboardingService:
    def __init__(self):
        self.tenant_service = TenantService("backend/logs/admin_monitoring.db")
        self.billing_service = BillingService()
        self.email_service = EmailService()
        
        # Define onboarding steps
        self.onboarding_steps = [
            OnboardingStep(
                id='account_setup',
                name='Account Setup',
                description='Create your account and verify email',
                status='pending',
                required=True,
                order=1
            ),
            OnboardingStep(
                id='choose_plan',
                name='Choose Plan',
                description='Select your subscription plan',
                status='pending',
                required=True,
                order=2
            ),
            OnboardingStep(
                id='upload_knowledge',
                name='Upload Knowledge Base',
                description='Upload your documents and content',
                status='pending',
                required=False,
                order=3
            ),
            OnboardingStep(
                id='test_chatbot',
                name='Test ChatBot',
                description='Try out your ChatBot with sample queries',
                status='pending',
                required=False,
                order=4
            ),
            OnboardingStep(
                id='customize_appearance',
                name='Customize Appearance',
                description='Brand your ChatBot with colors and messaging',
                status='pending',
                required=False,
                order=5
            ),
            OnboardingStep(
                id='get_api_keys',
                name='Get API Keys',
                description='Generate your API keys for integration',
                status='pending',
                required=True,
                order=6
            ),
            OnboardingStep(
                id='integration_setup',
                name='Integration Setup',
                description='Embed ChatBot or set up API integration',
                status='pending',
                required=False,
                order=7
            ),
            OnboardingStep(
                id='go_live',
                name='Go Live!',
                description='Launch your ChatBot for users',
                status='pending',
                required=False,
                order=8
            )
        ]
    
    async def start_onboarding(self, email: str, company_name: str, plan_type: str = 'free') -> Dict[str, Any]:
        """Start onboarding process for new tenant"""
        
        # Generate unique slug from company name
        slug = self._generate_slug(company_name)
        
        # Create tenant
        tenant = self.tenant_service.create_tenant(
            name=company_name,
            slug=slug,
            email=email,
            plan_type=plan_type
        )
        
        # Initialize onboarding progress
        progress = await self._initialize_onboarding_progress(tenant.id)
        
        # Mark first step as completed
        progress = await self._complete_step(tenant.id, 'account_setup')
        
        # Send welcome email
        await self.email_service.send_welcome_email(
            email=email,
            tenant_name=company_name,
            onboarding_url=f"https://app.yoursaas.com/onboarding/{tenant.slug}",
            api_keys={'public': tenant.api_key_public, 'private': tenant.api_key_private}
        )
        
        return {
            'tenant_id': tenant.id,
            'tenant_slug': slug,
            'onboarding_progress': progress,
            'api_keys': {
                'public': tenant.api_key_public,
                'private': tenant.api_key_private  # Only shown once
            }
        }
    
    async def get_onboarding_progress(self, tenant_id: int) -> OnboardingProgress:
        """Get current onboarding progress"""
        # This would typically be stored in database
        # For now, return default progress
        return OnboardingProgress(
            tenant_id=tenant_id,
            steps=self.onboarding_steps.copy(),
            current_step='choose_plan',
            completion_percentage=12,  # 1 of 8 steps
            started_at=datetime.now(),
            completed_at=None
        )
    
    async def complete_step(self, tenant_id: int, step_id: str) -> OnboardingProgress:
        """Mark onboarding step as completed"""
        return await self._complete_step(tenant_id, step_id)
    
    async def skip_step(self, tenant_id: int, step_id: str) -> OnboardingProgress:
        """Skip optional onboarding step"""
        step = next((s for s in self.onboarding_steps if s.id == step_id), None)
        if not step:
            raise ValueError(f"Invalid step: {step_id}")
        
        if step.required:
            raise ValueError(f"Cannot skip required step: {step_id}")
        
        # Update step status and return progress
        return await self._skip_step(tenant_id, step_id)
    
    async def handle_plan_selection(self, tenant_id: int, plan_id: str, billing_cycle: str = 'monthly') -> Dict[str, Any]:
        """Handle plan selection during onboarding"""
        
        if plan_id == 'free':
            # Update tenant plan (no billing needed)
            await self._update_tenant_plan(tenant_id, plan_id)
            await self._complete_step(tenant_id, 'choose_plan')
            
            return {
                'success': True,
                'message': 'Free plan activated',
                'next_step': 'upload_knowledge'
            }
        else:
            # Create subscription
            result = await self.billing_service.create_subscription(
                tenant_id=tenant_id,
                plan_id=plan_id,
                billing_cycle=billing_cycle
            )
            
            if result['status'] in ['active', 'trialing']:
                await self._complete_step(tenant_id, 'choose_plan')
                
                return {
                    'success': True,
                    'subscription_id': result['subscription_id'],
                    'message': f'{plan_id.title()} plan activated',
                    'next_step': 'upload_knowledge'
                }
            else:
                return {
                    'success': False,
                    'client_secret': result.get('client_secret'),
                    'message': 'Payment required to continue'
                }
    
    async def handle_knowledge_upload(self, tenant_id: int, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle knowledge base file uploads"""
        from backend.core.tenant_retriever import get_tenant_retriever
        
        try:
            # Get tenant retriever
            retriever = get_tenant_retriever(tenant_id)
            
            # Process uploaded files
            processed_count = 0
            for file_info in files:
                # Process and index file
                await self._process_knowledge_file(retriever, file_info)
                processed_count += 1
            
            if processed_count > 0:
                await self._complete_step(tenant_id, 'upload_knowledge')
            
            return {
                'success': True,
                'processed_files': processed_count,
                'message': f'Successfully processed {processed_count} files',
                'next_step': 'test_chatbot'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process knowledge base files'
            }
    
    # Private helper methods
    def _generate_slug(self, company_name: str) -> str:
        """Generate unique slug from company name"""
        import re
        base_slug = re.sub(r'[^a-zA-Z0-9]+', '-', company_name.lower()).strip('-')
        
        # Check if slug exists and make it unique
        counter = 1
        slug = base_slug
        while self.tenant_service.get_tenant_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    async def _initialize_onboarding_progress(self, tenant_id: int) -> OnboardingProgress:
        """Initialize onboarding progress in database"""
        # Implementation would store progress in database
        pass
    
    async def _complete_step(self, tenant_id: int, step_id: str) -> OnboardingProgress:
        """Mark step as completed and update progress"""
        # Implementation would update database and return progress
        pass
```

## Tenant Dashboard Frontend

### Vue.js Dashboard Structure

```
admin/tenant-dashboard/
├── src/
│   ├── components/
│   │   ├── onboarding/
│   │   │   ├── OnboardingWizard.vue
│   │   │   ├── StepAccountSetup.vue
│   │   │   ├── StepChoosePlan.vue
│   │   │   ├── StepUploadKnowledge.vue
│   │   │   ├── StepTestChatBot.vue
│   │   │   ├── StepCustomizeAppearance.vue
│   │   │   ├── StepApiKeys.vue
│   │   │   ├── StepIntegration.vue
│   │   │   └── StepGoLive.vue
│   │   ├── dashboard/
│   │   │   ├── DashboardOverview.vue
│   │   │   ├── UsageMetrics.vue
│   │   │   ├── QueryAnalytics.vue
│   │   │   └── QuickActions.vue
│   │   ├── knowledge/
│   │   │   ├── KnowledgeManager.vue
│   │   │   ├── FileUpload.vue
│   │   │   ├── DocumentsList.vue
│   │   │   └── IndexingStatus.vue
│   │   ├── chatbot/
│   │   │   ├── ChatBotInterface.vue
│   │   │   ├── ChatBotCustomizer.vue
│   │   │   ├── BrandingSettings.vue
│   │   │   └── ChatBotPreview.vue
│   │   └── settings/
│   │       ├── ApiKeyManager.vue
│   │       ├── TeamManagement.vue
│   │       ├── BillingSettings.vue
│   │       └── NotificationSettings.vue
│   ├── views/
│   │   ├── OnboardingView.vue
│   │   ├── DashboardView.vue
│   │   ├── KnowledgeView.vue
│   │   ├── ChatBotView.vue
│   │   ├── AnalyticsView.vue
│   │   └── SettingsView.vue
│   ├── stores/
│   │   ├── auth.js
│   │   ├── tenant.js
│   │   ├── onboarding.js
│   │   ├── knowledge.js
│   │   └── billing.js
│   └── services/
│       ├── api.js
│       ├── tenantApi.js
│       ├── uploadService.js
│       └── billingService.js
```

### Main Onboarding Component (`admin/tenant-dashboard/src/views/OnboardingView.vue`)

```vue
<template>
  <v-container fluid class="onboarding-container">
    <v-row justify="center">
      <v-col cols="12" lg="8" xl="6">
        <v-card class="onboarding-card" elevation="2">
          <v-card-title class="text-center pa-6">
            <h1 class="text-h4 font-weight-light">
              Welcome to {{ tenantName }}
            </h1>
            <p class="text-body-1 mt-2 text-medium-emphasis">
              Let's set up your AI-powered ChatBot in a few simple steps
            </p>
          </v-card-title>

          <!-- Progress Indicator -->
          <v-card-text>
            <v-stepper 
              v-model="currentStep" 
              :items="onboardingSteps"
              flat
              hide-actions
            >
              <template v-slot:item.1>
                <step-account-setup
                  :tenant="tenant"
                  @completed="handleStepComplete('account_setup')"
                />
              </template>

              <template v-slot:item.2>
                <step-choose-plan
                  :tenant="tenant"
                  :available-plans="availablePlans"
                  @plan-selected="handlePlanSelection"
                  @completed="handleStepComplete('choose_plan')"
                />
              </template>

              <template v-slot:item.3>
                <step-upload-knowledge
                  :tenant="tenant"
                  @files-uploaded="handleFilesUploaded"
                  @completed="handleStepComplete('upload_knowledge')"
                  @skipped="handleStepSkip('upload_knowledge')"
                />
              </template>

              <template v-slot:item.4>
                <step-test-chatbot
                  :tenant="tenant"
                  @tested="handleChatBotTested"
                  @completed="handleStepComplete('test_chatbot')"
                  @skipped="handleStepSkip('test_chatbot')"
                />
              </template>

              <template v-slot:item.5>
                <step-customize-appearance
                  :tenant="tenant"
                  @customized="handleAppearanceCustomized"
                  @completed="handleStepComplete('customize_appearance')"
                  @skipped="handleStepSkip('customize_appearance')"
                />
              </template>

              <template v-slot:item.6>
                <step-api-keys
                  :tenant="tenant"
                  :api-keys="apiKeys"
                  @keys-generated="handleApiKeysGenerated"
                  @completed="handleStepComplete('get_api_keys')"
                />
              </template>

              <template v-slot:item.7>
                <step-integration
                  :tenant="tenant"
                  :api-keys="apiKeys"
                  @integrated="handleIntegrationSetup"
                  @completed="handleStepComplete('integration_setup')"
                  @skipped="handleStepSkip('integration_setup')"
                />
              </template>

              <template v-slot:item.8>
                <step-go-live
                  :tenant="tenant"
                  @go-live="handleGoLive"
                  @completed="completeOnboarding"
                />
              </template>
            </v-stepper>
          </v-card-text>

          <!-- Navigation -->
          <v-card-actions class="pa-6">
            <v-btn
              variant="outlined"
              :disabled="currentStep === 1"
              @click="previousStep"
            >
              Previous
            </v-btn>
            <v-spacer />
            <v-btn
              color="primary"
              :disabled="!canProceed"
              @click="nextStep"
            >
              {{ currentStep === onboardingSteps.length ? 'Complete' : 'Next' }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Loading Overlay -->
    <v-overlay :model-value="loading" persistent>
      <v-progress-circular indeterminate color="primary" />
    </v-overlay>
  </v-container>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOnboardingStore } from '@/stores/onboarding'
import { useTenantStore } from '@/stores/tenant'

// Import step components
import StepAccountSetup from '@/components/onboarding/StepAccountSetup.vue'
import StepChoosePlan from '@/components/onboarding/StepChoosePlan.vue'
import StepUploadKnowledge from '@/components/onboarding/StepUploadKnowledge.vue'
import StepTestChatbot from '@/components/onboarding/StepTestChatBot.vue'
import StepCustomizeAppearance from '@/components/onboarding/StepCustomizeAppearance.vue'
import StepApiKeys from '@/components/onboarding/StepApiKeys.vue'
import StepIntegration from '@/components/onboarding/StepIntegration.vue'
import StepGoLive from '@/components/onboarding/StepGoLive.vue'

export default {
  name: 'OnboardingView',
  components: {
    StepAccountSetup,
    StepChoosePlan,
    StepUploadKnowledge,
    StepTestChatbot,
    StepCustomizeAppearance,
    StepApiKeys,
    StepIntegration,
    StepGoLive
  },
  setup() {
    const router = useRouter()
    const onboardingStore = useOnboardingStore()
    const tenantStore = useTenantStore()

    const currentStep = ref(1)
    const loading = ref(false)

    const tenant = computed(() => tenantStore.currentTenant)
    const tenantName = computed(() => tenant.value?.name || 'Your SaaS')
    const apiKeys = computed(() => tenantStore.apiKeys)
    const canProceed = computed(() => {
      // Logic to determine if current step is complete
      return onboardingStore.canProceedFromStep(currentStep.value)
    })

    const onboardingSteps = computed(() => [
      { title: 'Account Setup', value: 1 },
      { title: 'Choose Plan', value: 2 },
      { title: 'Upload Knowledge', value: 3 },
      { title: 'Test ChatBot', value: 4 },
      { title: 'Customize', value: 5 },
      { title: 'API Keys', value: 6 },
      { title: 'Integration', value: 7 },
      { title: 'Go Live', value: 8 }
    ])

    const availablePlans = computed(() => onboardingStore.availablePlans)

    // Methods
    const handleStepComplete = async (stepId) => {
      await onboardingStore.completeStep(stepId)
    }

    const handleStepSkip = async (stepId) => {
      await onboardingStore.skipStep(stepId)
    }

    const handlePlanSelection = async (planData) => {
      loading.value = true
      try {
        await onboardingStore.selectPlan(planData.planId, planData.billingCycle)
        await handleStepComplete('choose_plan')
      } finally {
        loading.value = false
      }
    }

    const handleFilesUploaded = async (files) => {
      loading.value = true
      try {
        await onboardingStore.uploadKnowledgeFiles(files)
        await handleStepComplete('upload_knowledge')
      } finally {
        loading.value = false
      }
    }

    const nextStep = () => {
      if (currentStep.value < onboardingSteps.value.length) {
        currentStep.value++
      } else {
        completeOnboarding()
      }
    }

    const previousStep = () => {
      if (currentStep.value > 1) {
        currentStep.value--
      }
    }

    const completeOnboarding = async () => {
      loading.value = true
      try {
        await onboardingStore.completeOnboarding()
        router.push('/dashboard')
      } finally {
        loading.value = false
      }
    }

    // Initialize
    onMounted(async () => {
      await onboardingStore.loadOnboardingProgress()
      currentStep.value = onboardingStore.currentStepNumber
    })

    return {
      currentStep,
      loading,
      tenant,
      tenantName,
      apiKeys,
      onboardingSteps,
      availablePlans,
      canProceed,
      handleStepComplete,
      handleStepSkip,
      handlePlanSelection,
      handleFilesUploaded,
      nextStep,
      previousStep,
      completeOnboarding
    }
  }
}
</script>

<style scoped>
.onboarding-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
}

.onboarding-card {
  max-width: 900px;
  margin: 0 auto;
}
</style>
```

### Onboarding Store (`admin/tenant-dashboard/src/stores/onboarding.js`)

```javascript
import { defineStore } from 'pinia'
import { tenantApi } from '@/services/tenantApi'
import { billingService } from '@/services/billingService'

export const useOnboardingStore = defineStore('onboarding', {
  state: () => ({
    progress: null,
    currentStepId: 'account_setup',
    completedSteps: [],
    skippedSteps: [],
    availablePlans: [
      {
        id: 'free',
        name: 'Free',
        price: { monthly: 0, yearly: 0 },
        features: ['100 queries/month', '10MB storage', 'Community support'],
        limits: { queries: 100, storage: 10 },
        recommended: false
      },
      {
        id: 'starter',
        name: 'Starter',
        price: { monthly: 29, yearly: 290 },
        features: ['1,000 queries/month', '100MB storage', 'Email support', 'Custom branding'],
        limits: { queries: 1000, storage: 100 },
        recommended: true
      },
      {
        id: 'pro',
        name: 'Pro',
        price: { monthly: 99, yearly: 990 },
        features: ['10,000 queries/month', '1GB storage', 'Priority support', 'Advanced analytics', 'Team management'],
        limits: { queries: 10000, storage: 1000 },
        recommended: false
      }
    ],
    loading: false,
    error: null
  }),

  getters: {
    currentStepNumber: (state) => {
      const steps = ['account_setup', 'choose_plan', 'upload_knowledge', 'test_chatbot', 'customize_appearance', 'get_api_keys', 'integration_setup', 'go_live']
      return steps.indexOf(state.currentStepId) + 1
    },

    completionPercentage: (state) => {
      return Math.round((state.completedSteps.length / 8) * 100)
    },

    canProceedFromStep: (state) => (stepNumber) => {
      const stepIds = ['account_setup', 'choose_plan', 'upload_knowledge', 'test_chatbot', 'customize_appearance', 'get_api_keys', 'integration_setup', 'go_live']
      const stepId = stepIds[stepNumber - 1]
      return state.completedSteps.includes(stepId) || state.skippedSteps.includes(stepId)
    }
  },

  actions: {
    async loadOnboardingProgress() {
      this.loading = true
      this.error = null
      
      try {
        const response = await tenantApi.getOnboardingProgress()
        this.progress = response.data
        this.currentStepId = response.data.current_step
        this.completedSteps = response.data.steps
          .filter(step => step.status === 'completed')
          .map(step => step.id)
        this.skippedSteps = response.data.steps
          .filter(step => step.status === 'skipped')
          .map(step => step.id)
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async completeStep(stepId) {
      try {
        await tenantApi.completeOnboardingStep(stepId)
        if (!this.completedSteps.includes(stepId)) {
          this.completedSteps.push(stepId)
        }
        // Remove from skipped if it was there
        this.skippedSteps = this.skippedSteps.filter(id => id !== stepId)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async skipStep(stepId) {
      try {
        await tenantApi.skipOnboardingStep(stepId)
        if (!this.skippedSteps.includes(stepId)) {
          this.skippedSteps.push(stepId)
        }
        // Remove from completed if it was there
        this.completedSteps = this.completedSteps.filter(id => id !== stepId)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async selectPlan(planId, billingCycle = 'monthly') {
      try {
        const response = await billingService.selectPlan({
          planId,
          billingCycle
        })
        
        if (response.data.success) {
          await this.completeStep('choose_plan')
          return response.data
        } else {
          throw new Error(response.data.message || 'Plan selection failed')
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async uploadKnowledgeFiles(files) {
      try {
        const response = await tenantApi.uploadKnowledgeFiles(files)
        if (response.data.success) {
          await this.completeStep('upload_knowledge')
          return response.data
        } else {
          throw new Error(response.data.message || 'File upload failed')
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async completeOnboarding() {
      try {
        await tenantApi.completeOnboarding()
        this.completedSteps.push('go_live')
      } catch (error) {
        this.error = error.message
        throw error
      }
    }
  }
})
```

## API Routes for Tenant Operations

### Onboarding API Routes (`backend/routes/onboarding.py`)

```python
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional
from backend.core.onboarding_service import OnboardingService
from backend.core.tenant_auth import tenant_auth, Tenant

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

class StartOnboardingRequest(BaseModel):
    email: EmailStr
    company_name: str
    plan_type: str = 'free'

class PlanSelectionRequest(BaseModel):
    plan_id: str
    billing_cycle: str = 'monthly'

@router.post("/start")
async def start_onboarding(request: StartOnboardingRequest):
    """Start onboarding process for new tenant"""
    onboarding_service = OnboardingService()
    
    try:
        result = await onboarding_service.start_onboarding(
            email=request.email,
            company_name=request.company_name,
            plan_type=request.plan_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/progress")
async def get_onboarding_progress(
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Get current onboarding progress"""
    onboarding_service = OnboardingService()
    
    try:
        progress = await onboarding_service.get_onboarding_progress(tenant.id)
        return progress
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/steps/{step_id}/complete")
async def complete_step(
    step_id: str,
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Complete onboarding step"""
    onboarding_service = OnboardingService()
    
    try:
        progress = await onboarding_service.complete_step(tenant.id, step_id)
        return {"success": True, "progress": progress}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/steps/{step_id}/skip")
async def skip_step(
    step_id: str,
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Skip optional onboarding step"""
    onboarding_service = OnboardingService()
    
    try:
        progress = await onboarding_service.skip_step(tenant.id, step_id)
        return {"success": True, "progress": progress}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/plan/select")
async def select_plan(
    request: PlanSelectionRequest,
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Handle plan selection during onboarding"""
    onboarding_service = OnboardingService()
    
    try:
        result = await onboarding_service.handle_plan_selection(
            tenant_id=tenant.id,
            plan_id=request.plan_id,
            billing_cycle=request.billing_cycle
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/knowledge/upload")
async def upload_knowledge_files(
    files: List[UploadFile] = File(...),
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Upload knowledge base files during onboarding"""
    onboarding_service = OnboardingService()
    
    try:
        # Process uploaded files
        file_data = []
        for file in files:
            content = await file.read()
            file_data.append({
                'filename': file.filename,
                'content': content,
                'content_type': file.content_type
            })
        
        result = await onboarding_service.handle_knowledge_upload(tenant.id, file_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Email Notification System

### Email Service (`backend/core/email_service.py`)

```python
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@yoursaas.com')
        
        # Initialize Jinja2 for email templates
        self.template_env = Environment(
            loader=FileSystemLoader('backend/templates/emails')
        )
    
    async def send_welcome_email(self, email: str, tenant_name: str, onboarding_url: str, api_keys: Dict[str, str]):
        """Send welcome email to new tenant"""
        template = self.template_env.get_template('welcome.html')
        
        html_content = template.render(
            tenant_name=tenant_name,
            onboarding_url=onboarding_url,
            api_key_public=api_keys['public'],
            api_key_private=api_keys['private']
        )
        
        await self._send_email(
            to_email=email,
            subject=f"Welcome to {tenant_name} - Your AI ChatBot is Ready!",
            html_content=html_content
        )
    
    async def send_payment_confirmation(self, email: str, tenant_name: str, plan_name: str, amount: float):
        """Send payment confirmation email"""
        template = self.template_env.get_template('payment_confirmation.html')
        
        html_content = template.render(
            tenant_name=tenant_name,
            plan_name=plan_name,
            amount=amount
        )
        
        await self._send_email(
            to_email=email,
            subject=f"Payment Confirmed - {plan_name} Plan Activated",
            html_content=html_content
        )
    
    async def send_usage_limit_warning(self, email: str, tenant_name: str, usage_type: str, percentage: int):
        """Send usage limit warning email"""
        template = self.template_env.get_template('usage_warning.html')
        
        html_content = template.render(
            tenant_name=tenant_name,
            usage_type=usage_type,
            percentage=percentage
        )
        
        await self._send_email(
            to_email=email,
            subject=f"Usage Warning - {percentage}% of {usage_type} limit reached",
            html_content=html_content
        )
    
    async def _send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None):
        """Send email using SMTP"""
        msg = MIMEMultipart('alternative')
        msg['From'] = self.from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Add text content if provided
        if text_content:
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            print(f"Email sent successfully to {to_email}")
        except Exception as e:
            print(f"Failed to send email to {to_email}: {str(e)}")
            raise
```

## Testing Strategy for Phase 2

### Integration Tests (`tests/integration/test_onboarding_flow.py`)

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

class TestOnboardingFlow:
    def test_complete_onboarding_flow(self):
        """Test complete onboarding flow from start to finish"""
        
        # Step 1: Start onboarding
        response = client.post("/api/v1/onboarding/start", json={
            "email": "test@company.com",
            "company_name": "Test Company",
            "plan_type": "free"
        })
        assert response.status_code == 200
        data = response.json()
        tenant_slug = data['tenant_slug']
        api_key = data['api_keys']['public']
        
        # Step 2: Get onboarding progress
        response = client.get("/api/v1/onboarding/progress", 
            headers={"Authorization": f"Bearer {api_key}"})
        assert response.status_code == 200
        
        # Step 3: Select plan
        response = client.post("/api/v1/onboarding/plan/select", 
            json={"plan_id": "starter", "billing_cycle": "monthly"},
            headers={"Authorization": f"Bearer {api_key}"})
        # Free tier - should succeed without payment
        assert response.status_code == 200
        
        # Step 4: Upload knowledge files (mock)
        # This would test file upload functionality
        
        # Step 5: Complete remaining steps
        steps_to_complete = ['test_chatbot', 'get_api_keys']
        for step in steps_to_complete:
            response = client.post(f"/api/v1/onboarding/steps/{step}/complete",
                headers={"Authorization": f"Bearer {api_key}"})
            assert response.status_code == 200
        
        # Verify tenant is properly set up
        response = client.get(f"/api/v1/tenants/{data['tenant_id']}/status",
            headers={"Authorization": f"Bearer {api_key}"})
        assert response.status_code == 200
        status_data = response.json()
        assert status_data['plan_type'] == 'free'
```

## Deployment Checklist for Phase 2

### Environment Variables
```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_STARTER_MONTHLY=price_...
STRIPE_PRICE_ID_STARTER_YEARLY=price_...
STRIPE_PRICE_ID_PRO_MONTHLY=price_...
STRIPE_PRICE_ID_PRO_YEARLY=price_...

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@yoursaas.com

# Frontend URLs
TENANT_DASHBOARD_URL=https://app.yoursaas.com
MARKETING_SITE_URL=https://yoursaas.com
```

### Pre-deployment Checklist
- [ ] Set up Stripe products and prices
- [ ] Configure email service (SMTP)
- [ ] Create email templates
- [ ] Run database migrations for billing tables
- [ ] Set up webhook endpoints for Stripe
- [ ] Test complete onboarding flow
- [ ] Build and deploy tenant dashboard frontend
- [ ] Configure domain and SSL for tenant dashboard

### Success Metrics
- [ ] New tenants can complete onboarding end-to-end
- [ ] Payment processing works correctly
- [ ] Usage limits are enforced
- [ ] Email notifications are sent
- [ ] Tenant dashboard is functional and responsive
- [ ] API key management works
- [ ] Knowledge base upload and indexing works

---

This completes the Phase 2 technical specifications. The phase focuses on creating a complete, revenue-generating SaaS product with proper billing, onboarding, and tenant management capabilities.