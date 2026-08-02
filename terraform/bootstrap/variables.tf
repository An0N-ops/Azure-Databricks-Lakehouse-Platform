variable "subscription_id" {
  type        = string
  description = "Target Azure Subscription ID for provisioning state backend resources."
}

variable "location" {
  type        = string
  description = "Azure Region for state backend resource placement."
  default     = "eastus2"
}

variable "environment" {
  type        = string
  description = "Environment designation (e.g., shared, dev, qa, prod)."
  default     = "shared"
}

variable "project_name" {
  type        = string
  description = "Project name prefix for standardized resource naming."
  default     = "lakehouse"
}
