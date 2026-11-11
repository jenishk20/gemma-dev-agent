class Profile < ApplicationRecord
  # Validates that username is present and unique
  validates :username, presence: true, uniqueness: true
  
  # Active Storage attachment for the PNG photo
  has_one_attached :profile_photo
end