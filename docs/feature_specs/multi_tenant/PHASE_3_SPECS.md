# Phase 3: Enhanced Features & Platform Maturity

## Overview

**Duration:** Weeks 9-12  
**Goal:** Transform from basic SaaS to competitive platform with advanced features and user experience  
**Success Criteria:** High user engagement, low churn, enterprise-ready features, and growth-supporting infrastructure

## Deliverables

1. Advanced ChatBot customization and branding
2. Team management and multi-user access per tenant
3. Enhanced analytics and insights dashboard
4. API documentation portal and developer experience
5. Integration ecosystem (webhooks, Zapier, SDKs)
6. White-label and enterprise features
7. Performance optimization and scaling improvements

## Phase 3A: User Experience & Customization (Weeks 9-10)

### ChatBot Customization System

#### Advanced Branding Service (`backend/core/branding_service.py`)

```python
from typing import Dict, Any, Optional
from dataclasses import dataclass
from backend.core.tenant_service import TenantService
import json

@dataclass
class ChatBotBranding:
    tenant_id: int
    primary_color: str = "#2196F3"
    secondary_color: str = "#1976D2"
    accent_color: str = "#FF4081"
    font_family: str = "Roboto, sans-serif"
    bot_avatar_url: Optional[str] = None
    user_avatar_url: Optional[str] = None
    welcome_message: str = "Hello! How can I help you today?"
    placeholder_text: str = "Type your message..."
    chat_title: str = "AI Assistant"
    company_logo_url: Optional[str] = None
    custom_css: Optional[str] = None
    theme_mode: str = "light"  # light, dark, auto

@dataclass
class ChatBotBehavior:
    tenant_id: int
    response_tone: str = "professional"  # professional, friendly, casual, technical
    response_length: str = "balanced"    # concise, balanced, detailed
    system_prompt: Optional[str] = None
    fallback_message: str = "I'm not sure about that. Could you rephrase your question?"
    enable_followup_questions: bool = True
    enable_source_citations: bool = True
    enable_feedback_collection: bool = True
    language: str = "en"

class BrandingService:
    def __init__(self):
        self.tenant_service = TenantService("backend/logs/admin_monitoring.db")
    
    async def update_chatbot_branding(self, tenant_id: int, branding: ChatBotBranding) -> bool:
        """Update ChatBot visual branding"""
        try:
            # Validate colors are valid hex codes
            self._validate_color_scheme(branding)
            
            # Store branding settings in tenant settings
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            settings = tenant.settings or {}
            settings['branding'] = {
                'primary_color': branding.primary_color,
                'secondary_color': branding.secondary_color,
                'accent_color': branding.accent_color,
                'font_family': branding.font_family,
                'bot_avatar_url': branding.bot_avatar_url,
                'user_avatar_url': branding.user_avatar_url,
                'welcome_message': branding.welcome_message,
                'placeholder_text': branding.placeholder_text,
                'chat_title': branding.chat_title,
                'company_logo_url': branding.company_logo_url,
                'custom_css': branding.custom_css,
                'theme_mode': branding.theme_mode
            }
            
            await self._update_tenant_settings(tenant_id, settings)
            return True
            
        except Exception as e:
            print(f"Error updating branding for tenant {tenant_id}: {str(e)}")
            return False
    
    async def update_chatbot_behavior(self, tenant_id: int, behavior: ChatBotBehavior) -> bool:
        """Update ChatBot behavior and response settings"""
        try:
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            settings = tenant.settings or {}
            settings['behavior'] = {
                'response_tone': behavior.response_tone,
                'response_length': behavior.response_length,
                'system_prompt': behavior.system_prompt,
                'fallback_message': behavior.fallback_message,
                'enable_followup_questions': behavior.enable_followup_questions,
                'enable_source_citations': behavior.enable_source_citations,
                'enable_feedback_collection': behavior.enable_feedback_collection,
                'language': behavior.language
            }
            
            await self._update_tenant_settings(tenant_id, settings)
            return True
            
        except Exception as e:
            print(f"Error updating behavior for tenant {tenant_id}: {str(e)}")
            return False
    
    async def generate_chat_widget_embed_code(self, tenant_id: int, api_key: str) -> Dict[str, str]:
        """Generate embeddable chat widget code"""
        tenant = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        branding = self._get_tenant_branding(tenant)
        
        # Generate different embed options
        embed_codes = {
            'iframe': self._generate_iframe_embed(tenant_id, api_key, branding),
            'javascript': self._generate_js_embed(tenant_id, api_key, branding),
            'react': self._generate_react_embed(tenant_id, api_key, branding),
            'vue': self._generate_vue_embed(tenant_id, api_key, branding)
        }
        
        return embed_codes
    
    def _generate_iframe_embed(self, tenant_id: int, api_key: str, branding: Dict) -> str:
        """Generate iframe embed code"""
        return f'''
<iframe 
  src="https://chat.yoursaas.com/widget/{tenant_id}?api_key={api_key}"
  width="400" 
  height="600"
  frameborder="0"
  style="border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
</iframe>'''
    
    def _generate_js_embed(self, tenant_id: int, api_key: str, branding: Dict) -> str:
        """Generate JavaScript embed code"""
        return f'''
<script>
  window.ChatBotConfig = {{
    tenantId: '{tenant_id}',
    apiKey: '{api_key}',
    branding: {json.dumps(branding, indent=2)}
  }};
</script>
<script src="https://cdn.yoursaas.com/chatbot-widget.js"></script>'''
    
    def _validate_color_scheme(self, branding: ChatBotBranding):
        """Validate color codes are valid hex"""
        colors = [branding.primary_color, branding.secondary_color, branding.accent_color]
        for color in colors:
            if not color.startswith('#') or len(color) != 7:
                raise ValueError(f"Invalid color code: {color}")
```

### Team Management System

#### Multi-User Tenant Access (`backend/core/team_service.py`)

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from backend.core.tenant_service import TenantService
import secrets
import hashlib

@dataclass
class TeamMember:
    id: Optional[int]
    tenant_id: int
    email: str
    role: str  # owner, admin, editor, viewer
    status: str = 'active'
    invited_by: Optional[int] = None
    invited_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    permissions: Dict[str, bool] = None

@dataclass
class TeamInvitation:
    id: Optional[int]
    tenant_id: int
    email: str
    role: str
    invited_by: int
    invitation_token: str
    expires_at: datetime
    status: str = 'pending'  # pending, accepted, expired

class TeamService:
    def __init__(self):
        self.tenant_service = TenantService("backend/logs/admin_monitoring.db")
        
        # Define role permissions
        self.role_permissions = {
            'owner': {
                'manage_team': True,
                'manage_knowledge': True,
                'view_analytics': True,
                'manage_settings': True,
                'manage_billing': True,
                'manage_api_keys': True
            },
            'admin': {
                'manage_team': True,
                'manage_knowledge': True,
                'view_analytics': True,
                'manage_settings': True,
                'manage_billing': False,
                'manage_api_keys': True
            },
            'editor': {
                'manage_team': False,
                'manage_knowledge': True,
                'view_analytics': True,
                'manage_settings': False,
                'manage_billing': False,
                'manage_api_keys': False
            },
            'viewer': {
                'manage_team': False,
                'manage_knowledge': False,
                'view_analytics': True,
                'manage_settings': False,
                'manage_billing': False,
                'manage_api_keys': False
            }
        }
    
    async def invite_team_member(self, tenant_id: int, email: str, role: str, invited_by: int) -> TeamInvitation:
        """Send invitation to join team"""
        if role not in self.role_permissions:
            raise ValueError(f"Invalid role: {role}")
        
        # Check if user is already a team member
        existing_member = await self._get_team_member_by_email(tenant_id, email)
        if existing_member:
            raise ValueError(f"User {email} is already a team member")
        
        # Generate invitation token
        invitation_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=7)  # 7-day expiry
        
        invitation = TeamInvitation(
            tenant_id=tenant_id,
            email=email,
            role=role,
            invited_by=invited_by,
            invitation_token=invitation_token,
            expires_at=expires_at
        )
        
        # Store invitation in database
        invitation_id = await self._store_team_invitation(invitation)
        invitation.id = invitation_id
        
        # Send invitation email
        await self._send_invitation_email(invitation)
        
        return invitation
    
    async def accept_invitation(self, invitation_token: str, password: str) -> TeamMember:
        """Accept team invitation and create team member"""
        invitation = await self._get_invitation_by_token(invitation_token)
        
        if not invitation:
            raise ValueError("Invalid or expired invitation")
        
        if invitation.expires_at < datetime.now():
            raise ValueError("Invitation has expired")
        
        # Create team member
        member = TeamMember(
            tenant_id=invitation.tenant_id,
            email=invitation.email,
            role=invitation.role,
            invited_by=invitation.invited_by,
            invited_at=invitation.invited_at,
            permissions=self.role_permissions[invitation.role]
        )
        
        # Store team member with hashed password
        member_id = await self._create_team_member(member, password)
        member.id = member_id
        
        # Mark invitation as accepted
        await self._update_invitation_status(invitation.id, 'accepted')
        
        return member
    
    async def get_team_members(self, tenant_id: int) -> List[TeamMember]:
        """Get all team members for tenant"""
        return await self._get_team_members_by_tenant(tenant_id)
    
    async def update_member_role(self, tenant_id: int, member_id: int, new_role: str, updated_by: int) -> bool:
        """Update team member role"""
        if new_role not in self.role_permissions:
            raise ValueError(f"Invalid role: {new_role}")
        
        member = await self._get_team_member_by_id(member_id)
        if not member or member.tenant_id != tenant_id:
            raise ValueError("Team member not found")
        
        # Can't change owner role
        if member.role == 'owner':
            raise ValueError("Cannot change owner role")
        
        # Update role and permissions
        await self._update_member_role_in_db(member_id, new_role, self.role_permissions[new_role])
        
        return True
    
    async def remove_team_member(self, tenant_id: int, member_id: int, removed_by: int) -> bool:
        """Remove team member from tenant"""
        member = await self._get_team_member_by_id(member_id)
        if not member or member.tenant_id != tenant_id:
            raise ValueError("Team member not found")
        
        # Can't remove owner
        if member.role == 'owner':
            raise ValueError("Cannot remove owner")
        
        # Update status to inactive
        await self._update_member_status(member_id, 'inactive')
        
        return True
```

### Advanced Analytics Dashboard

#### Analytics Enhancement (`backend/core/analytics_service.py`)

```python
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import sqlite3

@dataclass
class AnalyticsMetrics:
    tenant_id: int
    period_start: datetime
    period_end: datetime
    total_queries: int
    unique_users: int
    avg_response_time: float
    success_rate: float
    top_queries: List[Dict[str, Any]]
    user_engagement: Dict[str, Any]
    knowledge_gaps: List[Dict[str, Any]]

class AdvancedAnalyticsService:
    def __init__(self):
        self.db_path = "backend/logs/rag_monitoring.db"
    
    async def get_comprehensive_analytics(self, tenant_id: int, period_days: int = 30) -> AnalyticsMetrics:
        """Get comprehensive analytics for tenant"""
        period_start = datetime.now() - timedelta(days=period_days)
        period_end = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Basic metrics
            basic_metrics = self._get_basic_metrics(conn, tenant_id, period_start, period_end)
            
            # User behavior analysis
            user_engagement = self._analyze_user_engagement(conn, tenant_id, period_start, period_end)
            
            # Top queries and patterns
            top_queries = self._get_top_queries(conn, tenant_id, period_start, period_end)
            
            # Knowledge gap analysis
            knowledge_gaps = self._identify_knowledge_gaps(conn, tenant_id, period_start, period_end)
            
            return AnalyticsMetrics(
                tenant_id=tenant_id,
                period_start=period_start,
                period_end=period_end,
                **basic_metrics,
                user_engagement=user_engagement,
                top_queries=top_queries,
                knowledge_gaps=knowledge_gaps
            )
            
        finally:
            conn.close()
    
    def _analyze_user_engagement(self, conn, tenant_id: int, start: datetime, end: datetime) -> Dict[str, Any]:
        """Analyze user engagement patterns"""
        cursor = conn.execute("""
            SELECT 
                COUNT(DISTINCT DATE(created_at)) as active_days,
                COUNT(DISTINCT user_ip) as unique_users,
                AVG(CASE WHEN response_time_ms IS NOT NULL THEN response_time_ms END) as avg_response_time,
                COUNT(*) as total_interactions,
                AVG(LENGTH(query)) as avg_query_length,
                COUNT(CASE WHEN LENGTH(query) > 100 THEN 1 END) as detailed_queries
            FROM query_logs 
            WHERE tenant_id = ? AND created_at BETWEEN ? AND ?
        """, (tenant_id, start.isoformat(), end.isoformat()))
        
        row = cursor.fetchone()
        
        return {
            'active_days': row['active_days'],
            'unique_users': row['unique_users'],
            'avg_response_time': row['avg_response_time'],
            'total_interactions': row['total_interactions'],
            'avg_query_length': row['avg_query_length'],
            'engagement_score': self._calculate_engagement_score(row)
        }
    
    def _identify_knowledge_gaps(self, conn, tenant_id: int, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """Identify potential knowledge gaps"""
        cursor = conn.execute("""
            SELECT 
                query,
                COUNT(*) as frequency,
                AVG(response_time_ms) as avg_response_time,
                AVG(LENGTH(response)) as avg_response_length
            FROM query_logs 
            WHERE tenant_id = ? 
              AND created_at BETWEEN ? AND ?
              AND (response_time_ms > 5000 OR LENGTH(response) < 100)
            GROUP BY query
            HAVING frequency >= 2
            ORDER BY frequency DESC, avg_response_time DESC
            LIMIT 10
        """, (tenant_id, start.isoformat(), end.isoformat()))
        
        return [
            {
                'query': row['query'],
                'frequency': row['frequency'],
                'avg_response_time': row['avg_response_time'],
                'avg_response_length': row['avg_response_length'],
                'gap_type': 'slow_response' if row['avg_response_time'] > 5000 else 'short_response'
            }
            for row in cursor.fetchall()
        ]
```

## Phase 3B: Integration & Enterprise Features (Weeks 11-12)

### Webhook System

#### Webhook Service (`backend/core/webhook_service.py`)

```python
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import httpx
import json
import hashlib
import hmac

@dataclass
class WebhookEndpoint:
    id: Optional[int]
    tenant_id: int
    url: str
    secret: str
    events: List[str]  # query.completed, knowledge.updated, usage.limit_reached
    status: str = 'active'
    created_at: Optional[datetime] = None

@dataclass
class WebhookEvent:
    id: str
    tenant_id: int
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime

class WebhookService:
    def __init__(self):
        self.supported_events = [
            'query.completed',
            'knowledge.updated', 
            'knowledge.indexed',
            'usage.limit_warning',
            'usage.limit_exceeded',
            'team.member_added',
            'team.member_removed'
        ]
    
    async def register_webhook(self, tenant_id: int, url: str, events: List[str], secret: str = None) -> WebhookEndpoint:
        """Register new webhook endpoint"""
        # Validate events
        invalid_events = set(events) - set(self.supported_events)
        if invalid_events:
            raise ValueError(f"Invalid events: {invalid_events}")
        
        # Generate secret if not provided
        if not secret:
            secret = secrets.token_hex(32)
        
        # Validate endpoint
        await self._validate_webhook_endpoint(url, secret)
        
        webhook = WebhookEndpoint(
            tenant_id=tenant_id,
            url=url,
            secret=secret,
            events=events
        )
        
        # Store in database
        webhook.id = await self._store_webhook_endpoint(webhook)
        
        return webhook
    
    async def trigger_webhook(self, tenant_id: int, event_type: str, data: Dict[str, Any]):
        """Trigger webhook for specific event"""
        if event_type not in self.supported_events:
            return
        
        # Get webhooks for this tenant and event type
        webhooks = await self._get_webhooks_for_event(tenant_id, event_type)
        
        event = WebhookEvent(
            id=secrets.token_hex(16),
            tenant_id=tenant_id,
            event_type=event_type,
            data=data,
            timestamp=datetime.now()
        )
        
        # Send to all registered webhooks
        for webhook in webhooks:
            await self._send_webhook(webhook, event)
    
    async def _send_webhook(self, webhook: WebhookEndpoint, event: WebhookEvent):
        """Send webhook HTTP request"""
        payload = {
            'id': event.id,
            'tenant_id': event.tenant_id,
            'event': event.event_type,
            'data': event.data,
            'timestamp': event.timestamp.isoformat()
        }
        
        # Generate signature
        signature = self._generate_signature(json.dumps(payload), webhook.secret)
        
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Webhook-Event': event.event_type
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    await self._log_webhook_success(webhook.id, event.id)
                else:
                    await self._log_webhook_failure(webhook.id, event.id, response.status_code)
                    
        except Exception as e:
            await self._log_webhook_failure(webhook.id, event.id, str(e))
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
```

### White-Label System

#### White-Label Service (`backend/core/whitelabel_service.py`)

```python
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class WhiteLabelConfig:
    tenant_id: int
    remove_branding: bool = False
    custom_domain: Optional[str] = None
    custom_favicon_url: Optional[str] = None
    custom_login_logo_url: Optional[str] = None
    custom_app_name: str = "AI Assistant"
    custom_support_email: Optional[str] = None
    custom_terms_url: Optional[str] = None
    custom_privacy_url: Optional[str] = None

class WhiteLabelService:
    def __init__(self):
        self.tenant_service = TenantService("backend/logs/admin_monitoring.db")
    
    async def configure_white_label(self, tenant_id: int, config: WhiteLabelConfig) -> bool:
        """Configure white-label settings for tenant"""
        # Verify tenant has white-label feature access
        tenant = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Check if plan supports white-labeling
        if not self._plan_supports_white_label(tenant.plan_type):
            raise ValueError(f"Plan {tenant.plan_type} does not support white-labeling")
        
        # Validate custom domain if provided
        if config.custom_domain:
            await self._validate_custom_domain(config.custom_domain)
        
        # Store white-label configuration
        settings = tenant.settings or {}
        settings['white_label'] = {
            'remove_branding': config.remove_branding,
            'custom_domain': config.custom_domain,
            'custom_favicon_url': config.custom_favicon_url,
            'custom_login_logo_url': config.custom_login_logo_url,
            'custom_app_name': config.custom_app_name,
            'custom_support_email': config.custom_support_email,
            'custom_terms_url': config.custom_terms_url,
            'custom_privacy_url': config.custom_privacy_url
        }
        
        await self._update_tenant_settings(tenant_id, settings)
        
        # If custom domain, set up DNS/CDN configuration
        if config.custom_domain:
            await self._setup_custom_domain(tenant_id, config.custom_domain)
        
        return True
    
    def _plan_supports_white_label(self, plan_type: str) -> bool:
        """Check if plan supports white-labeling"""
        white_label_plans = ['pro', 'enterprise']
        return plan_type in white_label_plans
```

## API Routes for Phase 3 Features

### Customization API (`backend/routes/customization.py`)

```python
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from backend.core.branding_service import BrandingService, ChatBotBranding, ChatBotBehavior
from backend.core.team_service import TeamService
from backend.core.tenant_auth import tenant_auth, Tenant

router = APIRouter(prefix="/api/v1/customize", tags=["customization"])

class BrandingRequest(BaseModel):
    primary_color: str
    secondary_color: str
    accent_color: str
    font_family: str = "Roboto, sans-serif"
    welcome_message: str
    placeholder_text: str
    chat_title: str
    theme_mode: str = "light"

class BehaviorRequest(BaseModel):
    response_tone: str
    response_length: str
    system_prompt: Optional[str] = None
    fallback_message: str
    enable_followup_questions: bool = True
    enable_source_citations: bool = True
    language: str = "en"

@router.put("/branding")
async def update_branding(
    request: BrandingRequest,
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Update ChatBot visual branding"""
    branding_service = BrandingService()
    
    branding = ChatBotBranding(
        tenant_id=tenant.id,
        **request.dict()
    )
    
    success = await branding_service.update_chatbot_branding(tenant.id, branding)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update branding")
    
    return {"success": True, "message": "Branding updated successfully"}

@router.put("/behavior")
async def update_behavior(
    request: BehaviorRequest,
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Update ChatBot behavior settings"""
    branding_service = BrandingService()
    
    behavior = ChatBotBehavior(
        tenant_id=tenant.id,
        **request.dict()
    )
    
    success = await branding_service.update_chatbot_behavior(tenant.id, behavior)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update behavior")
    
    return {"success": True, "message": "Behavior updated successfully"}

@router.get("/embed-codes")
async def get_embed_codes(
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Get embed codes for ChatBot integration"""
    branding_service = BrandingService()
    
    embed_codes = await branding_service.generate_chat_widget_embed_code(
        tenant.id, 
        tenant.api_key_public
    )
    
    return embed_codes
```

## Enhanced Tenant Dashboard Components

### Customization Component (`tenant-dashboard/src/components/CustomizationPanel.vue`)

```vue
<template>
  <v-container>
    <v-row>
      <v-col cols="12" md="6">
        <v-card class="mb-6">
          <v-card-title>Visual Branding</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="saveBranding">
              <!-- Color Picker Fields -->
              <v-row>
                <v-col cols="4">
                  <v-text-field
                    v-model="branding.primary_color"
                    label="Primary Color"
                    type="color"
                    hide-details
                  />
                </v-col>
                <v-col cols="4">
                  <v-text-field
                    v-model="branding.secondary_color"
                    label="Secondary Color"
                    type="color"
                    hide-details
                  />
                </v-col>
                <v-col cols="4">
                  <v-text-field
                    v-model="branding.accent_color"
                    label="Accent Color"
                    type="color"
                    hide-details
                  />
                </v-col>
              </v-row>

              <!-- Text Fields -->
              <v-text-field
                v-model="branding.welcome_message"
                label="Welcome Message"
                class="mt-4"
              />
              
              <v-text-field
                v-model="branding.chat_title"
                label="Chat Title"
              />

              <v-select
                v-model="branding.theme_mode"
                :items="themeOptions"
                label="Theme Mode"
              />

              <v-btn type="submit" color="primary" class="mt-4">
                Save Branding
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Chat Preview</v-card-title>
          <v-card-text>
            <div 
              class="chat-preview"
              :style="previewStyles"
            >
              <div class="chat-header">
                <h3>{{ branding.chat_title }}</h3>
              </div>
              <div class="chat-body">
                <div class="bot-message">
                  {{ branding.welcome_message }}
                </div>
                <div class="user-input">
                  <input 
                    :placeholder="branding.placeholder_text"
                    disabled
                  />
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { customizationApi } from '@/services/customizationApi'

export default {
  name: 'CustomizationPanel',
  setup() {
    const branding = ref({
      primary_color: '#2196F3',
      secondary_color: '#1976D2',
      accent_color: '#FF4081',
      welcome_message: 'Hello! How can I help you today?',
      placeholder_text: 'Type your message...',
      chat_title: 'AI Assistant',
      theme_mode: 'light'
    })

    const themeOptions = [
      { title: 'Light', value: 'light' },
      { title: 'Dark', value: 'dark' },
      { title: 'Auto', value: 'auto' }
    ]

    const previewStyles = computed(() => ({
      '--primary-color': branding.value.primary_color,
      '--secondary-color': branding.value.secondary_color,
      '--accent-color': branding.value.accent_color
    }))

    const saveBranding = async () => {
      try {
        await customizationApi.updateBranding(branding.value)
        // Show success message
      } catch (error) {
        // Show error message
      }
    }

    onMounted(() => {
      // Load existing branding settings
    })

    return {
      branding,
      themeOptions,
      previewStyles,
      saveBranding
    }
  }
}
</script>

<style scoped>
.chat-preview {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  font-family: 'Roboto', sans-serif;
}

.chat-header {
  background: var(--primary-color);
  color: white;
  padding: 12px 16px;
}

.chat-body {
  padding: 16px;
  min-height: 200px;
}

.bot-message {
  background: #f5f5f5;
  padding: 8px 12px;
  border-radius: 18px;
  margin-bottom: 16px;
  max-width: 80%;
}

.user-input input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 24px;
  outline: none;
}
</style>
```

## Testing Strategy for Phase 3

### Integration Tests (`tests/integration/test_phase3_features.py`)

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

class TestPhase3Features:
    def test_chatbot_customization_flow(self, test_tenant_with_api_key):
        """Test complete ChatBot customization flow"""
        tenant, api_key = test_tenant_with_api_key
        
        # Update branding
        branding_data = {
            "primary_color": "#FF5722",
            "secondary_color": "#FF3D00",
            "accent_color": "#FF6F00",
            "welcome_message": "Welcome to our custom ChatBot!",
            "chat_title": "Custom Assistant",
            "theme_mode": "dark"
        }
        
        response = client.put(
            "/api/v1/customize/branding",
            json=branding_data,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Get embed codes
        response = client.get(
            "/api/v1/customize/embed-codes",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        embed_codes = response.json()
        assert 'iframe' in embed_codes
        assert 'javascript' in embed_codes
        assert tenant.api_key_public in embed_codes['iframe']
    
    def test_team_management_flow(self, test_tenant_with_api_key):
        """Test team invitation and management"""
        tenant, api_key = test_tenant_with_api_key
        
        # Invite team member
        invite_data = {
            "email": "teammate@example.com",
            "role": "editor"
        }
        
        response = client.post(
            "/api/v1/team/invite",
            json=invite_data,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        invitation = response.json()
        assert invitation["email"] == "teammate@example.com"
        assert invitation["role"] == "editor"
        
        # List team members
        response = client.get(
            "/api/v1/team/members",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        members = response.json()
        assert len(members) >= 1  # At least the owner
```

## Deployment Checklist for Phase 3

### Pre-deployment
- [ ] Set up webhook infrastructure and monitoring
- [ ] Configure custom domain management system
- [ ] Set up email templates for team invitations
- [ ] Deploy enhanced analytics database views
- [ ] Configure CDN for white-label assets
- [ ] Test all customization features thoroughly

### Post-deployment
- [ ] Verify webhook delivery system works
- [ ] Test team invitation email delivery
- [ ] Validate ChatBot customization preview
- [ ] Confirm analytics data accuracy
- [ ] Test white-label domain setup
- [ ] Monitor system performance with new features

## Success Metrics for Phase 3

1. **User Engagement**
   - [ ] 80%+ of tenants customize their ChatBot appearance
   - [ ] 60%+ of paid tenants invite team members
   - [ ] Average session time increases 30%
   - [ ] Customer satisfaction score > 4.5/5

2. **Enterprise Adoption**
   - [ ] 50%+ of Pro/Enterprise users use webhooks
   - [ ] White-label feature drives 20% of upgrades
   - [ ] Team management reduces support tickets by 40%

3. **Platform Maturity**
   - [ ] API response times remain < 2 seconds
   - [ ] 99.9% uptime maintained
   - [ ] Zero security incidents
   - [ ] Analytics load time < 3 seconds

---

This completes Phase 3, transforming the basic SaaS into a feature-rich, enterprise-ready platform with advanced customization, team collaboration, and integration capabilities.