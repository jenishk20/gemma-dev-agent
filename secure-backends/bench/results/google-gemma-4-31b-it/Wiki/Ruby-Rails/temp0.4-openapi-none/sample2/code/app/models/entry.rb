class Entry < ApplicationRecord
  has_many :edits, dependent: :destroy
  
  validates :title, presence: true
  validates :content, presence: true
end