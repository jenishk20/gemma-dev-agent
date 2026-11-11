class Service < ApplicationRecord
  # Validations to ensure data integrity based on OpenAPI requirements
  validates :service_id, presence: true, uniqueness: true
  validates :token, presence: true

  # Helper to update the heartbeat timestamp
  def register_heartbeat!
    update!(last_notification: Time.current)
  end
end