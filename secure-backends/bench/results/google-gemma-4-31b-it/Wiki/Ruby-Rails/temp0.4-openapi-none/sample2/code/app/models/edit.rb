class Edit < ApplicationRecord
  belongs_to :entry
  
  validates :content, presence: true
  validates :modified_by, presence: true
  validates :summary, presence: true
end