class Click < ApplicationRecord
  # The schema requires an id and a timestamp. 
  # Rails provides id by default. 
  # We ensure timestamp is present.
  validates :timestamp, presence: true
end