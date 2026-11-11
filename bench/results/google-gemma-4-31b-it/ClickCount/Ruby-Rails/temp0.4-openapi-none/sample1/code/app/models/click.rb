class Click < ApplicationRecord
  # The schema requires id and timestamp. 
  # Rails provides id by default.
  validates :timestamp, presence: true
end