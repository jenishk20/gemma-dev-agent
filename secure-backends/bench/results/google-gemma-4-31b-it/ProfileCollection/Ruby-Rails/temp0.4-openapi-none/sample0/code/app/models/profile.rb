class Profile < ApplicationRecord
  # Profile photo is stored using Active Storage
  has_one_attached :profile_photo

  validates :username, presence: true, uniqueness: true
  validates :profile_page, presence: true
end