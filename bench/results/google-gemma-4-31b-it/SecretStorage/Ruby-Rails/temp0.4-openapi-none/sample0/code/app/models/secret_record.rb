class SecretRecord < ApplicationRecord
  # We use a separate model for secrets to keep User model clean
  # Table columns: user_id (integer), secret_text (text)
  belongs_to :user
end