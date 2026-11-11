class ServiceStatus < ApplicationRecord
  # Validations to ensure data integrity
  validates :service_id, presence: true
  validates :token, presence: true

  # We use a unique index on service_id in the DB, 
  # so we handle updates via find_or_initialize_by
end