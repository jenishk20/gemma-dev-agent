class Edit < ApplicationRecord
  belongs_to :entry
  validates :content, :modified_by, :summary, presence: true
end