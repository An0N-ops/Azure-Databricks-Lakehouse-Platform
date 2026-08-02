variable "project_name" {
  type        = string
  description = "Project name prefix."
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, qa, prod)."
}

variable "location" {
  type        = string
  description = "Azure Region for resource group placement."
}

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags to append to the resource group."
  default     = {}
}
